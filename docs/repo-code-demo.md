# Repo Code Diagnosis Demo

This demo implements the first read-only code evidence loop:

```text
diagnosis request
-> problem parsing
-> registered repo scan
-> code keyword search
-> module/commit recall
-> evidence-backed diagnosis response
```

## Demo Repo

The simulated repo lives at:

```text
apps/api/app/data/demo_repos/demo-runtime
```

It is registered in:

```text
apps/api/app/data/repos.json
```

For production, keep real repos outside this project, for example:

```text
/data/dcu-repos/repo-runtime
/data/dcu-repos/repo-driver
/data/dcu-repos/repo-framework
```

Then update `repos.json` to use those absolute paths, or replace `RepoRegistry`
with a PostgreSQL-backed repo registry.

## Demo APIs

```text
GET  /api/v1/repos
GET  /api/v1/repos/files
GET  /api/v1/tools/search-code?q=device&q=hipInit
POST /api/v1/diagnose
```

## Production Replacement Points

- Replace `RepoRegistry.scan_files()` with a scanner that writes to PostgreSQL.
- Replace `CodeSearchTool.search_code()` internals with `rg`.
- Replace `COMMITS.json` with `git log` ingestion into PostgreSQL.
- Put docs, cases, module cards, and commit summaries into Milvus.
- Keep raw code in mounted read-only repos, not in Milvus.
