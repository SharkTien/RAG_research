import html
import re
import unicodedata


class NormalizeService:
    """Structure-aware cleaning and LlamaIndex ingestion for Docling elements."""

    _control_chars = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _spaces = re.compile(r"[ \t]+")
    _blank_lines = re.compile(r"\n{3,}")
    _image_marker = re.compile(r"<!--\s*image\s*-->", re.IGNORECASE)
    _page_number = re.compile(r"^(?:page|trang)\s+\d{1,4}(?:\s+(?:of|trên)\s+\d{1,4})?$", re.IGNORECASE)

    def __init__(self):
        self._pipeline = None

    @classmethod
    def clean_text(cls, text: str) -> str:
        text = html.unescape(text or "")
        text = unicodedata.normalize("NFKC", text)
        text = cls._control_chars.sub("", text)
        text = cls._image_marker.sub("\n[IMAGE]\n", text)
        text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text, flags=re.UNICODE)
        lines = [cls._spaces.sub(" ", line).strip() for line in text.splitlines()]
        return cls._blank_lines.sub("\n\n", "\n".join(lines)).strip()

    @staticmethod
    def _signature(text: str) -> str:
        """Compare repeated OCR noise without depending on diacritics."""
        decomposed = unicodedata.normalize("NFKD", text)
        ascii_like = "".join(char for char in decomposed if not unicodedata.combining(char))
        return re.sub(r"[^a-zA-Z0-9]+", "", ascii_like).lower()

    @classmethod
    def _elements_from_docling(cls, doc_json: dict) -> list[dict]:
        elements = []
        for index, item in enumerate(doc_json.get("texts", [])):
            text = cls.clean_text(item.get("text", ""))
            if not text:
                continue
            provenance = item.get("prov", []) or [{}]
            for prov_index, prov in enumerate(provenance):
                bbox = prov.get("bbox") or {}
                elements.append({
                    "element_id": item.get("self_ref", f"#/texts/{index}"),
                    "text": text,
                    "page": prov.get("page_no"),
                    "bbox": {
                        "left": bbox.get("l"), "bottom": bbox.get("b"),
                        "right": bbox.get("r"), "top": bbox.get("t"),
                    } if bbox else None,
                    "coord_origin": bbox.get("coord_origin") if bbox else None,
                    "element_type": item.get("label", "text"),
                    "provenance_index": prov_index,
                })
        # Docling usually emits reading order, but OCR-heavy brochures and
        # slides can interleave elements from different layout regions.
        return sorted(
            elements,
            key=lambda element: (
                element["page"] if element.get("page") is not None else 0,
                -(element.get("bbox") or {}).get("top", 0),
                (element.get("bbox") or {}).get("left", 0),
            ),
        )

    @classmethod
    def _remove_structural_noise(cls, elements: list[dict]) -> list[dict]:
        page_count = len({e["page"] for e in elements if e.get("page") is not None})
        if page_count < 3:
            return elements
        signatures_by_page: dict[str, set[int]] = {}
        for element in elements:
            signature = cls._signature(element["text"])
            page = element.get("page")
            if signature and page is not None:
                signatures_by_page.setdefault(signature, set()).add(page)
        repeated_signatures = {
            signature for signature, pages in signatures_by_page.items()
            if len(signature) <= 180
            and len(pages) >= max(3, int(page_count * 0.6))
        }
        return [
            element for element in elements
            if cls._signature(element["text"]) not in repeated_signatures
            and not cls._page_number.fullmatch(element["text"])
            and not (
                len(element["text"]) <= 4
                and not re.search(r"[\wÀ-ỹĐđ]", element["text"], re.UNICODE)
            )
        ]

    def _get_pipeline(self):
        if self._pipeline is None:
            from llama_index.core.ingestion import IngestionPipeline
            from llama_index.core.node_parser import SentenceSplitter
            self._pipeline = IngestionPipeline(
                transformations=[SentenceSplitter(chunk_size=1000, chunk_overlap=150)]
            )
        return self._pipeline

    def normalize(self, doc_json: dict, document_metadata: dict) -> tuple[str, list[dict]]:
        """Clean Docling text while preserving element-level provenance.

        Chunking/embedding is intentionally not performed here.  This stage
        produces the normalized representation that a later ingestion step
        can consume.
        """
        elements = self._remove_structural_noise(self._elements_from_docling(doc_json))
        if not elements:
            return "", []

        normalized_elements = [
            {**element, "metadata": {**document_metadata, **{
                "element_id": element["element_id"],
                "page": element["page"],
                "bbox": element["bbox"],
                "coord_origin": element["coord_origin"],
                "element_type": element["element_type"],
            }}}
            for element in elements
        ]
        return "\n\n".join(element["text"] for element in elements), normalized_elements

    def ingest(self, doc_json: dict, document_metadata: dict) -> tuple[str, list[dict]]:
        """Create LlamaIndex chunks for the later ingestion phase."""
        clean_text, elements = self.normalize(doc_json, document_metadata)
        if not elements:
            return clean_text, []

        from llama_index.core import Document
        documents = [
            Document(
                text=element["text"],
                metadata=element["metadata"],
            )
            for element in elements
        ]
        nodes = self._get_pipeline().run(documents=documents, show_progress=False)
        chunks = [{
            "id": node.node_id,
            "text": node.get_content(),
            "metadata": node.metadata,
        } for node in nodes]
        return clean_text, chunks

    def chunk_text(self, text: str, document_metadata: dict) -> list[dict]:
        """Chunk already-normalized semantic text without performing embedding."""
        if not text.strip():
            return []
        from llama_index.core import Document
        nodes = self._get_pipeline().run(documents=[Document(text=text, metadata=document_metadata)], show_progress=False)
        return [{"id": node.node_id, "text": node.get_content(), "metadata": node.metadata} for node in nodes]
