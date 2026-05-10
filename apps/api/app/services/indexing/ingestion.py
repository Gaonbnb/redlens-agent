from pathlib import Path

from app.services.indexing.repo_registry import RepoRegistry
from app.services.rag.milvus_store import MilvusKnowledgeStore
from app.services.storage.postgres import PostgresStore


class RepoIngestionService:
    """Ingest repo/file/commit/module metadata into PostgreSQL."""

    def __init__(
        self,
        repo_registry: RepoRegistry,
        postgres: PostgresStore,
        milvus: MilvusKnowledgeStore | None = None,
    ) -> None:
        self.repo_registry = repo_registry
        self.postgres = postgres
        self.milvus = milvus or MilvusKnowledgeStore()

    def run(self) -> dict:
        modules = self.repo_registry.module_cards()
        commits = self.repo_registry.load_commits()
        self._ingest_vector_knowledge(modules, commits)

        if not self.postgres.enabled:
            return {"status": "disabled", "run_id": 0, "repos": 0, "files": 0, "commits": 0, "modules": 0}

        self.postgres.ensure_schema()
        with self.postgres.connect() as connection:
            run_id = connection.execute(
                "insert into ingestion_runs(status) values ('running') returning id"
            ).fetchone()["id"]
            try:
                repo_count = self._ingest_repos(connection)
                files = self.repo_registry.scan_files()
                file_count = self._ingest_files(connection, files)
                commit_count = self._ingest_commits(connection, commits)
                module_count = self._ingest_modules(connection, modules)
                connection.execute(
                    """
                    update ingestion_runs
                    set status = 'completed',
                        finished_at = now(),
                        repos_count = %s,
                        files_count = %s,
                        commits_count = %s,
                        modules_count = %s
                    where id = %s
                    """,
                    (repo_count, file_count, commit_count, module_count, run_id),
                )
                connection.commit()
                return {
                    "status": "completed",
                    "run_id": run_id,
                    "repos": repo_count,
                    "files": file_count,
                    "commits": commit_count,
                    "modules": module_count,
                }
            except Exception as exc:
                connection.execute(
                    "update ingestion_runs set status = 'failed', finished_at = now(), error = %s where id = %s",
                    (str(exc), run_id),
                )
                connection.commit()
                raise

    def _repo_ids(self, connection) -> dict[str, int]:
        rows = connection.execute("select id, name from repos").fetchall()
        return {row["name"]: row["id"] for row in rows}

    def _ingest_repos(self, connection) -> int:
        count = 0
        for repo in self.repo_registry.repos:
            connection.execute(
                """
                insert into repos(name, path, repo_type, default_branch)
                values (%s, %s, %s, %s)
                on conflict (name) do update set
                    path = excluded.path,
                    repo_type = excluded.repo_type,
                    default_branch = excluded.default_branch,
                    updated_at = now()
                """,
                (repo.name, str(repo.path), repo.repo_type, repo.default_branch),
            )
            count += 1
        return count

    def _ingest_files(self, connection, files: list[dict]) -> int:
        repo_ids = self._repo_ids(connection)
        for item in files:
            suffix = Path(item["file_path"]).suffix.lower()
            connection.execute(
                """
                insert into files(repo_id, file_path, language, suffix, size_bytes)
                values (%s, %s, %s, %s, %s)
                on conflict (repo_id, file_path) do update set
                    language = excluded.language,
                    suffix = excluded.suffix,
                    size_bytes = excluded.size_bytes,
                    updated_at = now()
                """,
                (repo_ids[item["repo"]], item["file_path"], item["language"], suffix, item["size_bytes"]),
            )
        return len(files)

    def _ingest_commits(self, connection, commits: list[dict]) -> int:
        repo_ids = self._repo_ids(connection)
        for item in commits:
            connection.execute(
                """
                insert into commits(repo_id, hash, message, author, committed_at, keywords, summary)
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (repo_id, hash) do update set
                    message = excluded.message,
                    author = excluded.author,
                    committed_at = excluded.committed_at,
                    keywords = excluded.keywords,
                    summary = excluded.summary
                """,
                (
                    repo_ids[item["repo"]],
                    item["hash"],
                    item["message"],
                    item.get("author"),
                    item.get("committed_at") or item.get("date"),
                    item.get("keywords", []),
                    item.get("summary"),
                ),
            )
        return len(commits)

    def _ingest_modules(self, connection, modules: list[dict]) -> int:
        repo_ids = self._repo_ids(connection)
        for item in modules:
            connection.execute(
                """
                insert into modules(
                    id, repo_id, name, directory_paths, keywords, typical_questions,
                    key_entry_files, versions, chips, frameworks, description
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    repo_id = excluded.repo_id,
                    name = excluded.name,
                    directory_paths = excluded.directory_paths,
                    keywords = excluded.keywords,
                    typical_questions = excluded.typical_questions,
                    key_entry_files = excluded.key_entry_files,
                    versions = excluded.versions,
                    chips = excluded.chips,
                    frameworks = excluded.frameworks,
                    description = excluded.description,
                    updated_at = now()
                """,
                (
                    item["id"],
                    repo_ids[item["repo"]],
                    item["name"],
                    item.get("paths", []),
                    item.get("keywords", item.get("tags", [])),
                    item.get("typical_questions", []),
                    item.get("key_entry_files", item.get("key_files", [])),
                    item.get("versions", []),
                    item.get("chips", []),
                    item.get("frameworks", []),
                    item.get("description", ""),
                ),
            )
        return len(modules)

    def _ingest_vector_knowledge(self, modules: list[dict], commits: list[dict]) -> int:
        items = []
        for module in modules:
            text = " ".join(
                [
                    module.get("name", ""),
                    module.get("description", ""),
                    " ".join(module.get("tags", [])),
                    " ".join(module.get("typical_questions", [])),
                    " ".join(module.get("key_entry_files", [])),
                ]
            )
            items.append(
                {
                    "id": f"module:{module['repo']}:{module['id']}",
                    "source_type": "module",
                    "title": module["name"],
                    "text": text,
                }
            )
        for commit in commits:
            text = " ".join([commit.get("message", ""), commit.get("summary", ""), " ".join(commit.get("keywords", []))])
            items.append(
                {
                    "id": f"commit:{commit['repo']}:{commit['hash']}",
                    "source_type": "commit",
                    "title": commit["hash"],
                    "text": text,
                }
            )
        return self.milvus.upsert_texts(items)
