"""Semantic document normalization through the existing OpenAI-compatible Qwen service."""

import json
import os
import re
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "http://host.docker.internal:8027/v1").rstrip("/")
QWEN_MODEL = os.getenv("QWEN_MODEL", "a2genesis/Qwen3.8-27B-NVFP4")
QWEN_TIMEOUT = int(os.getenv("QWEN_TIMEOUT_SECONDS", "180"))
QWEN_MAX_INPUT_CHARS = int(os.getenv("QWEN_MAX_INPUT_CHARS", "16000"))

SYSTEM_PROMPT = """You are a semantic document normalization engine and OCR post-processor.
Normalize only the supplied document text. You MAY correct obvious OCR transcription errors and Vietnamese diacritics when the correction is unambiguous from the surrounding text (for example, 'ké từ' -> 'kể từ', 'nội dụng' -> 'nội dung').
You MUST NOT invent, continue, complete, translate, summarize away, or infer facts.
Never change or fabricate names, numbers, dates, legal references, units, identifiers, or substantive meaning. If a correction is uncertain, preserve the source text and add a warning.
The supplied text may be truncated. If it ends in the middle of a document, STOP at that exact boundary.
Every output element must be a cleaning/reformatting of a supplied source element. Do not add any element that is not supplied.
Do not reconstruct missing pages or continue a table of contents.
Preserve numbers, names, dates, units, page references, and source element ids exactly when present; only repair surrounding OCR characters, not their values.
Return a PATCH only. Do not repeat unchanged elements. Return ONLY valid JSON matching this schema:
{
  "title": string|null,
  "sections": [{"heading": string|null, "level": integer, "element_ids": [string]}],
  "corrections": [{"element_id": string, "text": string}],
  "types": [{"element_id": string, "type": "title|heading|paragraph|list|table|caption|footer|unknown"}],
  "warnings": [string]
}
Only include an item in corrections when its text genuinely needs an unambiguous OCR correction.
Only include an item in types when its semantic type needs to change.
If nothing needs changing, return empty corrections and types arrays. Do not include markdown fences or commentary."""


def _json_from_response(content: str) -> dict:
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if fenced:
        content = fenced.group(1).strip()
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Qwen output không chứa JSON object")
    json_text = content[start:end + 1]
    try:
        value = json.loads(json_text)
    except json.JSONDecodeError:
        # Qwen/vLLM occasionally emits valid objects but misses a comma between
        # adjacent array items or top-level fields. Repair only structural
        # newlines; JSON string newlines are escaped and cannot match these.
        repaired = re.sub(r"}\s*\n\s*{", "},\n{", json_text)
        repaired = re.sub(r'([}\]])\s*\n(\s*)"([A-Za-z_][A-Za-z0-9_]*)"\s*:', r'\1,\n\2"\3":', repaired)
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        value = json.loads(repaired)
    if not isinstance(value, dict):
        raise ValueError("Qwen output không phải JSON object")
    return value


def _validate(value: dict, source_elements: list[dict]) -> dict:
    if not {"sections", "corrections", "types", "warnings"}.issubset(value):
        raise ValueError("Thiếu trường bắt buộc trong semantic normalization")
    if not all(isinstance(value[key], list) for key in ("sections", "corrections", "types", "warnings")):
        raise ValueError("Schema semantic normalization không hợp lệ")
    source_ids = {str(item.get("element_id")) for item in source_elements}
    corrections = {
        str(item.get("element_id")): str(item.get("text", ""))
        for item in value["corrections"]
        if isinstance(item, dict) and str(item.get("element_id")) in source_ids
    }
    allowed_types = {"title", "heading", "paragraph", "list", "table", "caption", "footer", "unknown"}
    type_updates = {
        str(item.get("element_id")): item.get("type")
        for item in value["types"]
        if isinstance(item, dict)
        and str(item.get("element_id")) in source_ids
        and item.get("type") in allowed_types
    }
    normalized = []
    for item in source_elements:
        element_id = str(item.get("element_id"))
        source_type = item.get("element_type", "unknown")
        normalized.append({
            "element_id": element_id,
            "type": type_updates.get(element_id, source_type if source_type in allowed_types else "unknown"),
            "text": corrections.get(element_id, str(item.get("text", ""))),
            "page": item.get("page"),
        })
    source_text = "\n".join(str(item.get("text", "")) for item in source_elements)
    normalized_text = "\n".join(item["text"] for item in normalized)
    if len(normalized_text) > max(len(source_text) * 1.25, len(source_text) + 300):
        raise ValueError("Qwen output dài bất thường so với raw input; từ chối kết quả mở rộng tài liệu")
    source_tokens = set(re.findall(r"[\wÀ-ỹ]+", source_text.casefold()))
    normalized_tokens = re.findall(r"[\wÀ-ỹ]+", normalized_text.casefold())
    if normalized_tokens:
        novel_ratio = sum(token not in source_tokens for token in normalized_tokens) / len(normalized_tokens)
        if novel_ratio > 0.30:
            raise ValueError("Qwen output chứa quá nhiều nội dung không có trong raw input")
    return {
        "title": value.get("title"),
        "sections": value["sections"],
        "elements": normalized,
        "warnings": [str(item) for item in value["warnings"]],
    }


def _normalize_window(clean_text: str, source_elements: list[dict]) -> tuple[dict | None, str | None]:
    """Normalize one bounded source window."""
    selected_elements = []
    element_chars = 0
    for item in source_elements:
        compact = {
            "element_id": item.get("element_id"),
            "text": item.get("text", ""),
            "page": item.get("page"),
            "element_type": item.get("element_type"),
        }
        item_chars = len(json.dumps(compact, ensure_ascii=False))
        if element_chars + item_chars > QWEN_MAX_INPUT_CHARS:
            break
        selected_elements.append(compact)
        element_chars += item_chars
    payload = {
        "document": {
            "text": clean_text[:QWEN_MAX_INPUT_CHARS],
            "truncated": len(clean_text) > QWEN_MAX_INPUT_CHARS,
            "elements": selected_elements,
            "elements_truncated": len(selected_elements) < len(source_elements),
        }
    }
    request_payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0,
        "max_tokens": 4096,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    try:
        last_error = None
        for attempt in range(2):
            request_body = json.dumps(request_payload).encode("utf-8")
            request = Request(f"{QWEN_BASE_URL}/chat/completions", data=request_body, headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=QWEN_TIMEOUT) as response:
                result = json.loads(response.read().decode("utf-8"))
            choice = result["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            try:
                if finish_reason == "length":
                    raise ValueError("Qwen output bị cắt do chạm giới hạn output token")
                return _validate(_json_from_response(content), selected_elements), None
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == 0:
                    request_payload["messages"].append({"role": "user", "content": "Your previous output was invalid JSON. Return the PATCH JSON object again. Keep corrections and types minimal; do not repeat unchanged elements."})
                    time.sleep(0.5)
        raise ValueError(str(last_error))
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            detail = str(exc)
        return None, f"Qwen semantic normalization failed: HTTP {exc.code}: {detail}"
    except (URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return None, f"Qwen semantic normalization failed: {exc}"


def normalize(clean_text: str, source_elements: list[dict]) -> tuple[dict | None, str | None]:
    """Normalize all source elements in bounded windows without dropping the tail."""
    if not source_elements:
        return None, "Qwen semantic normalization failed: không có source element"

    windows = []
    current = []
    current_chars = 0
    for item in source_elements:
        compact_size = len(json.dumps({
            "element_id": item.get("element_id"),
            "text": item.get("text", ""),
            "page": item.get("page"),
            "element_type": item.get("element_type"),
        }, ensure_ascii=False))
        if current and current_chars + compact_size > QWEN_MAX_INPUT_CHARS:
            windows.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += compact_size
    if current:
        windows.append(current)

    merged_elements = []
    merged_sections = []
    warnings = []
    title = None
    print(f"Qwen normalization windows={len(windows)} elements={len(source_elements)} max_input_chars={QWEN_MAX_INPUT_CHARS}", flush=True)
    for index, window in enumerate(windows, start=1):
        window_text = "\n\n".join(str(item.get("text", "")) for item in window)
        print(f"Qwen batch {index}/{len(windows)} start elements={len(window)} chars={len(window_text)}", flush=True)
        result, error = _normalize_window(window_text, window)
        if error or not result:
            print(f"Qwen batch {index}/{len(windows)} failed: {error}", flush=True)
            return None, error or "Qwen semantic normalization failed: empty result"
        print(f"Qwen batch {index}/{len(windows)} done output_elements={len(result.get('elements', []))}", flush=True)
        title = title or result.get("title")
        merged_elements.extend(result.get("elements", []))
        merged_sections.extend(result.get("sections", []))
        warnings.extend(result.get("warnings", []))

    # Restore source order even if a model reorders elements inside a window.
    order = {str(item.get("element_id")): index for index, item in enumerate(source_elements)}
    merged_elements.sort(key=lambda item: order.get(str(item.get("element_id")), 10**9))
    return {
        "title": title,
        "sections": merged_sections,
        "elements": merged_elements,
        "warnings": warnings,
    }, None
