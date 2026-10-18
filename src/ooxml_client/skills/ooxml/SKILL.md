---
name: ooxml
description: Read, locate, validate and compare OOXML files (pptx, docx, xlsx). Use when the
  user asks to analyze/inspect/compare/validate Office documents, including Chinese requests
  such as 分析/检查/比对/校验/读取/定位 Office 文档（pptx/docx/xlsx）.
---

# OOXML document operations

## Invocation

Every operation takes one JSON object via `--params '<JSON>'` (or `--params-file <path>`).
There is no `key=value` syntax.

If `ooxml` is not on PATH, run `ooxml --version` first; when the runtime is not on PATH,
pass `--runtime-python /abs/path/bin/python`.

## Workflow (in order)

1. Catalogue: `ooxml man --params '{"topic": "operations", "output": "summary"}'`
   — list operation IDs, descriptions and target types; do not read full schemas first.
2. Structure: `ooxml inspect --params '{"path": "/abs/x.pptx"}'`
   — overview; use `{"path": "...", "view": "layout", "output": "summary"}` for PPTX layouts.
3. Locate: `ooxml locate --params '{"path": "/abs/x.pptx", "view": "slides", "output": "summary", "limit": 20}'`
   — reuse returned target paths; paginate with `limit`/`offset`.
4. Read: `ooxml view --params '{"path": "/abs/x.pptx", "target": "slides[0]"}'`
   — `target` may be an array; `mode` is `detail/summary/text/xml`.
5. Validate: `ooxml validate --params '{"path": "/abs/x.pptx", "level": "structural"}'`
   — `level` may be `schema` or `semantic`; always validate before delivering.
6. Compare: `ooxml diff --params '{"before": "/abs/a.pptx", "after": "/abs/b.pptx"}'`
   — default `modes` are `["opc","xml","semantic"]`; structural is PPTX-only.

## Habits (fail closed)

- Input is read-only: never modify the source file; prove it with an unchanged file hash.
- Editing is out of scope for this skill. When the user explicitly asks for changes, run
  `ooxml apply --params '{"path": "...", "output_path": "...", "operation_id": "...", "target": "...", "params": {...}}'`
  and always write to a new output file.
- Report validation findings before delivering a result; never ignore findings silently.

## Trigger example

"分析合同.docx" → man(operations) → inspect → locate → view (as needed) → validate → report
structure, content and validation conclusions.
