## Wiki

Project wiki and documentation are located at: `C:\Users\User\First\notes\claude-vault\wiki`

Consult the wiki for architecture references, flow documentation, DB schema, and retrospectives before implementing features.

## Wiki Ingestion

When document or research materials are added or substantially changed, use a `wiki-ingest` subagent to document the work in the project wiki.

Trigger wiki ingestion when:

- New research notes, specs, PDFs, transcripts, reports, or planning documents are added.
- Existing source documents are substantially revised.
- Implementation work depends on external research or non-code project documents.
- A user explicitly asks to ingest, add to wiki, document this, or update wiki.

Pass the subagent:

- Exact source file paths, preferably from `raw/`, `docs/`, `research/`, exports, or user-provided attachments.
- Related feature, workflow, database, architecture, or operating procedure context.
- Whether the task should create a new wiki page, update an existing page, or only update indexes/logs.

Expected wiki updates:

- Create or update the relevant structured wiki page under `C:\Users\User\First\notes\claude-vault\wiki`.
- Add links to related architecture, flow, DB schema, operating procedure, or retrospective pages where appropriate.
- Update relevant index pages so the new material is discoverable.
- Add an ingestion/log entry with the source file, date, summary, and resulting wiki page path.

Constraints:

- Do not write outside the allowed workspace or the configured wiki path without explicit user permission.
- If sandbox permissions do not allow writing to the wiki path, request approval before making changes.
- Preserve source documents; do not delete, move, or rewrite source files unless explicitly requested.
- Keep ingestion scoped to documentation. Do not implement code changes as part of wiki ingestion unless separately requested.
