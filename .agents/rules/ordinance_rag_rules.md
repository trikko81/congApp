# OrdinanceRAG Rules & Guidelines

## 1. Citation & Grounding Rules
- **Traceability Guarantee**: Every claim or summarized statement generated from retrieved city council records MUST attach precise source metadata containing document name, page number, and paragraph number.
- **Strict Citation Format**: Citations in responses must format as hyperlinked inline badges: `[DocName, Page X, ¶Y]`.

## 2. Code Quality & Standards
- **Python 3.10+**:
  - Enforce strict typing (`typing` module) for all function signatures.
  - Follow PEP 8 guidelines. Use f-strings for string formatting.
  - Exception handling required for all IO, PDF extraction, and vector DB queries.
- **Next.js & React (TypeScript)**:
  - Strict TypeScript types. Avoid `any`.
  - Maintain a clean split-screen UI layout (Left: Chat & citations, Right: PDF viewer with auto-scroll highlighting).

## 3. Storage & Artifact Rules
- Keep source code organized under designated frontend and backend subdirectories.
- Avoid writing loose temporary files outside of designated scratch directories.
