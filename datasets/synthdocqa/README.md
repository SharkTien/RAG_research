---
license: apache-2.0
task_categories:
- question-answering
- document-question-answering
tags:
- document-understanding
- synthetic
- pdf
- tables
- forms
- figures
- annotations
- rag
- benchmark
pretty_name: SynthDocQA
size_categories:
- 1K<n<10K
language:
- en
---

# SynthDocQA

A benchmark dataset for evaluating document understanding and question-answering systems on complex, realistic synthetic business documents.

## Overview

SynthDocQA contains **9,798 questions** grounded in **100 synthetic PDF documents** spanning diverse business domains and document types. Each question is tied to a specific element in a document (table, figure, form, annotation, or text block) and comes with structured assertions defining the expected answer.

The dataset is designed to evaluate RAG pipelines, PDF parsers, and document understanding models on multi-modal, real-world-style business content.

## Contents

| File / Folder | Description |
|---|---|
| `ALL_queries.json` | All 9,798 QA pairs with grounding references and assertions |
| `grounding_pdfs_v2/` | 100 synthetic PDF documents (stored via Git LFS) |
| `manifest_files/` | 100 JSON manifests with full document structure metadata |

## Dataset Statistics

| Metric | Value |
|---|---|
| Total questions | 9,798 |
| Total documents | 100 |
| Questions per document | ~98 |
| Element types | 5 |
| Document recipe types | 24 |

### Questions by Element Type

| Element Type | Count | % |
|---|---|---|
| table | 3,961 | 40.4% |
| figure | 2,899 | 29.6% |
| form | 1,496 | 15.3% |
| annotation | 941 | 9.6% |
| text_block | 501 | 5.1% |

### Documents by Recipe Type (top 10)

| Recipe | Questions |
|---|---|
| data_focused | 2,129 |
| compliance_report | 1,190 |
| mixed_document | 1,133 |
| field_ops | 702 |
| forms_workflow | 697 |
| executive_visual | 590 |
| annotation_heavy | 425 |
| research_paper | 421 |
| balanced_equal | 411 |
| scanned_archive | 393 |

## Data Schema

### `ALL_queries.json`

A JSON array of query objects. Each entry has the following structure:

```json
{
  "Id": "Q1",
  "query": "What is the total revenue reported in Q3?",
  "refs": [
    {
      "filePath": "doc_0000_s1045958549.pdf",
      "element_type": "table",
      "Artifact_ID": "table_003",
      "data_source": "compliance_report"
    }
  ],
  "assertions": [
    "The answer should mention the specific dollar value from the table.",
    "The answer should reference Q3 specifically."
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `Id` | string | Unique question ID (`Q1`–`Q9798`) |
| `query` | string | The natural language question |
| `refs[].filePath` | string | PDF filename containing the answer |
| `refs[].element_type` | string | One of: `table`, `figure`, `form`, `annotation`, `text_block` |
| `refs[].Artifact_ID` | string | Unique element identifier within the document |
| `refs[].data_source` | string | Document recipe/template type |
| `assertions` | array[string] | Criteria the correct answer must satisfy |

### `manifest_files/doc_0000_s<seed>.json`

Each manifest describes the full structure of a document:

```json
{
  "doc_id": "doc_0000_s1045958549",
  "title": "...",
  "subtitle": "...",
  "topic_id": "annual_report",
  "recipe_name": "compliance_report",
  "seed": 1045958549,
  "files": { "pdf": "grounding_pdfs_v2/doc_0000_s1045958549.pdf" },
  "document_brief": {
    "narrative_theme": "...",
    "sections": [...],
    "tables": [...],
    "charts": [...]
  },
  "structure": [
    {
      "element_type": "table",
      "Artifact_ID": "table_003",
      "caption": "...",
      "qa_candidates": [...]
    }
  ]
}
```

## Document Topics

The 100 documents span 50+ business domains including:

- Financial performance and annual reports
- M&A due diligence and valuation
- Regulatory compliance assessments
- Supply chain and procurement
- Customer experience and NPS analysis
- Employee engagement surveys
- Clinical data analysis
- ESG and sustainability reports
- Cloud migration and IT strategy
- Product launch readiness
- Workforce analytics
- Capital expenditure proposals

## Usage

```python
import json

# Load all queries
with open("ALL_queries.json") as f:
    queries = json.load(f)

print(f"Total queries: {len(queries)}")

# Filter to table questions only
table_qs = [q for q in queries if any(r["element_type"] == "table" for r in q["refs"])]
print(f"Table questions: {len(table_qs)}")

# Load a manifest
with open("manifest_files/doc_0000_s1045958549.json") as f:
    manifest = json.load(f)

print(f"Document: {manifest['title']}")
print(f"Recipe: {manifest['recipe_name']}")
print(f"Elements: {len(manifest['structure'])}")
```

## License

Apache 2.0