from pathlib import Path

from app.services.indexing.repo_registry import RepoRegistry


class CodeSearchTool:
    """Small grep-like search over registered repos.

    This demo intentionally uses Python scanning so it works everywhere.
    Replace the internals with ripgrep for the production server.
    """

    def __init__(self, repo_registry: RepoRegistry) -> None:
        self.repo_registry = repo_registry

    def search_code(self, queries: list[str], max_results: int = 20) -> list[dict]:
        normalized_queries = [query.lower() for query in queries if query.strip()]
        if not normalized_queries:
            return []

        matches: list[dict] = []
        for repo in self.repo_registry.repos:
            for path in repo.path.rglob("*"):
                if not path.is_file() or path.name == "COMMITS.json":
                    continue
                if path.suffix.lower() not in {".cpp", ".cc", ".cxx", ".h", ".hpp", ".py", ".md", ".txt"}:
                    continue

                lines = self._read_lines(path)
                for index, line in enumerate(lines, start=1):
                    haystack = line.lower()
                    hit_terms = [query for query in normalized_queries if query in haystack]
                    if not hit_terms:
                        continue
                    matches.append(
                        {
                            "repo": repo.name,
                            "file_path": path.relative_to(repo.path).as_posix(),
                            "line": index,
                            "text": line.strip(),
                            "hit_terms": hit_terms,
                            "context": self._context(lines, index),
                        }
                    )
                    if len(matches) >= max_results:
                        return matches
        return matches

    def read_file_slice(self, repo_name: str, file_path: str, start_line: int, end_line: int) -> dict:
        repo = self.repo_registry.get_repo(repo_name)
        target = (repo.path / file_path).resolve()
        if repo.path not in target.parents and target != repo.path:
            raise ValueError("File path escapes registered repo")

        lines = self._read_lines(target)
        start = max(1, start_line)
        end = min(len(lines), end_line)
        return {
            "repo": repo_name,
            "file_path": file_path,
            "start_line": start,
            "end_line": end,
            "content": "".join(lines[start - 1 : end]),
        }

    def _read_lines(self, path: Path) -> list[str]:
        try:
            return path.read_text(encoding="utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1").splitlines(keepends=True)

    def _context(self, lines: list[str], line_number: int) -> list[str]:
        start = max(1, line_number - 1)
        end = min(len(lines), line_number + 1)
        return [line.rstrip("\n") for line in lines[start - 1 : end]]
