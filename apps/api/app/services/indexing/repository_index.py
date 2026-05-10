# 代码索引 用于存储和检索代码模块、提交记录、案例
from app.services.indexing.repo_registry import RepoRegistry


class RepositoryIndex:
    """In-memory metadata index built from registered repos.

    Production should persist the same shape into PostgreSQL. This demo keeps
    it in memory to make the full flow easy to inspect and replace.
    """

    def __init__(self, repo_registry: RepoRegistry | None = None) -> None:
        self.repo_registry = repo_registry or RepoRegistry()
        self.modules = self.repo_registry.module_cards()
        self.commits = self.repo_registry.load_commits()

    def list_modules(self) -> list[dict]:
        return self.modules

    def get_module(self, module_id: str) -> dict:
        for item in self.modules:
            if item["id"] == module_id:
                return item
        raise KeyError(f"Module {module_id} not found")

    def list_files(self) -> list[dict]:
        return self.repo_registry.scan_files()

    def rank_modules(self, keywords: list[str]) -> list[dict]:
        ranked = []
        for module in self.modules:
            terms = " ".join(module.get("tags", []) + module.get("paths", []) + [module.get("name", "")]).lower()
            hit_keywords = [keyword for keyword in keywords if keyword.lower() in terms]
            if hit_keywords:
                score = len(hit_keywords)
                ranked.append(
                    {
                        "id": module["id"],
                        "name": module["name"],
                        "score": round(min(0.99, 0.45 + score * 0.12), 2),
                        "reason": f"Matched module tags/paths: {', '.join(hit_keywords)}",
                    }
                )

        if not ranked and self.modules:
            ranked = [
                {
                    "id": self.modules[0]["id"],
                    "name": self.modules[0]["name"],
                    "score": 0.42,
                    "reason": "Default runtime fallback when no explicit module tag matched.",
                }
            ]

        return sorted(ranked, key=lambda item: item["score"], reverse=True)

    def related_files(self, module_ids: list[str]) -> list[str]:
        files = []
        scanned_files = self.repo_registry.scan_files()
        for module in self.modules:
            if module["id"] not in module_ids:
                continue
            repo_name = module["repo"]
            for scanned_file in scanned_files:
                if scanned_file["repo"] != repo_name:
                    continue
                if any(scanned_file["file_path"].startswith(path) for path in module.get("paths", [])):
                    files.append(f"{repo_name}:{scanned_file['file_path']}")
        return files[:8]

    def related_commits(self, keywords: list[str]) -> list[dict]:
        matched = []
        for commit in self.commits:
            haystack = f"{commit['message']} {' '.join(commit.get('keywords', []))}".lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                matched.append(commit)
        return matched[:5]
