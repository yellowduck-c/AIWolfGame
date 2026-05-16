# Errors

Command failures and integration errors.

---

## [ERR-20260516-001] read_tool_parameters

**Logged**: 2026-05-16T00:00:00Z
**Priority**: low
**Status**: pending
**Area**: docs

### Summary
Read tool calls failed because an empty `pages` parameter was passed for Markdown files.

### Error
```
Invalid pages parameter: "". Use formats like "1-5", "3", or "10-20". Pages are 1-indexed.
```

### Context
- Operation attempted: reading Markdown files with the Read tool.
- Incorrect parameter: `pages: ""`.
- Correct approach: omit optional parameters entirely when they are not needed; only pass `pages` for PDFs with a real page range.

### Suggested Fix
When calling Read for non-PDF files, include only `file_path`, `offset`, and `limit` as needed.

### Metadata
- Reproducible: yes
- Related Files: none
- See Also: none

---

## [ERR-20260516-002] frontend_scaffold_path

**Logged**: 2026-05-16T00:00:00Z
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
Frontend build failed because the Vite scaffold did not generate the expected config files in the intended project directory.

### Error
```
error TS5083: Cannot read file 'd:/WorkSpace/AIWolfGame/ai_werewolf_frontend/tsconfig.json'.
```

### Context
- Operation attempted: building the frontend after running `npm create vite@latest` with an absolute Windows path.
- The generator reported output under a nested unexpected path, so required files such as `tsconfig.json` were not created in `d:/WorkSpace/AIWolfGame/ai_werewolf_frontend`.
- Assumption that scaffolding succeeded in the target directory was incorrect.

### Suggested Fix
After running project generators, verify the actual output path and confirm that required generated files exist before proceeding with installation or build steps.

### Metadata
- Reproducible: yes
- Related Files: ai_werewolf_frontend/package.json
- See Also: none

---

## [ERR-20260516-003] backend_port_conflict

**Logged**: 2026-05-16T00:00:00Z
**Priority**: low
**Status**: pending
**Area**: backend

### Summary
Backend startup verification failed because port 8000 was already occupied by another process.

### Error
```
[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)
```

### Context
- Operation attempted: starting the FastAPI server with Uvicorn in the `ai-werewolf` conda environment.
- Application startup completed successfully before the bind step failed.
- This indicates an environment conflict on the chosen port rather than an import or app bootstrap failure.

### Suggested Fix
When verifying backend startup, retry on another port or inspect active listeners before treating the app as broken.

### Metadata
- Reproducible: yes
- Related Files: werewolf_agent_backend/main.py
- See Also: none

---
