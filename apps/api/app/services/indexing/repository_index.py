# RepositoryIndex: 代码索引服务
# 负责存储和检索代码模块、提交记录、历史案例等元数据
# 支持内存模式（demo）和 PostgreSQL 持久化模式（生产环境）
from app.services.indexing.repo_registry import RepoRegistry
from app.services.storage.postgres import PostgresStore


class RepositoryIndex:
    """In-memory metadata index built from registered repos.

    Production should persist the same shape into PostgreSQL. This demo keeps
    it in memory to make the full flow easy to inspect and replace.
    """

    def __init__(self, repo_registry: RepoRegistry | None = None, postgres: PostgresStore | None = None) -> None:
        # repo_registry: 仓库注册表，用于获取仓库配置和文件列表
        # postgres: PostgreSQL 存储（可选，用于持久化）
        self.repo_registry = repo_registry or RepoRegistry()
        self.postgres = postgres or PostgresStore()
        # 从仓库注册表加载模块和提交数据
        self.modules = self.repo_registry.module_cards()
        self.commits = self.repo_registry.load_commits()

    # 获取所有模块列表，优先从 PostgreSQL 获取（如果启用）
    def list_modules(self) -> list[dict]:
        if self.postgres.enabled:
            modules = self._postgres_modules()
            if modules:
                return modules
        return self.modules

    # 根据模块ID获取模块详情
    def get_module(self, module_id: str) -> dict:
        for item in self.list_modules():
            if item["id"] == module_id:
                return item
        raise KeyError(f"Module {module_id} not found")

    # 获取所有仓库的文件列表，优先从 PostgreSQL 获取（如果启用）
    def list_files(self) -> list[dict]:
        if self.postgres.enabled:
            files = self._postgres_files()
            if files:
                return files
        return self.repo_registry.scan_files()

    # rank_modules: 基于关键词对模块进行打分排序
    # 匹配逻辑：综合考虑 tags, keywords, paths, typical_questions, key_entry_files, name, description
    # 返回分数最高的模块列表（降序排列）
    def rank_modules(self, keywords: list[str]) -> list[dict]:
        ranked = []
        modules = self.list_modules()
        for module in modules:
            # 合并所有文本字段用于匹配
            terms = " ".join(
                module.get("tags", [])
                + module.get("keywords", [])
                + module.get("paths", [])
                + module.get("typical_questions", [])
                + module.get("key_entry_files", [])
                + [module.get("name", ""), module.get("description", "")]
            ).lower()
            # 找出命中的关键词
            hit_keywords = [keyword for keyword in keywords if keyword.lower() in terms]
            if hit_keywords:
                score = len(hit_keywords)
                ranked.append(
                    {
                        "id": module["id"],
                        "repo": module.get("repo"),
                        "name": module["name"],
                        "description": module.get("description", ""),
                        # 分数计算：基础分0.45 + 命中关键词数*0.12，上限0.99
                        "score": round(min(0.99, 0.45 + score * 0.12), 2),
                        "reason": f"Matched module tags/paths: {', '.join(hit_keywords)}",
                    }
                )

        # 如果没有匹配，返回第一个模块作为默认回退
        if not ranked and modules:
            ranked = [
                {
                    "id": modules[0]["id"],
                    "repo": modules[0].get("repo"),
                    "name": modules[0]["name"],
                    "description": modules[0].get("description", ""),
                    "score": 0.42,
                    "reason": "Default runtime fallback when no explicit module tag matched.",
                }
            ]

        return sorted(ranked, key=lambda item: item["score"], reverse=True)

    # related_files: 根据模块ID列表获取相关的文件路径
    # 逻辑：遍历模块的 paths 字段，匹配文件列表中的文件
    def related_files(self, module_ids: list[str]) -> list[str]:
        files = []
        scanned_files = self.list_files()
        for module in self.list_modules():
            if module["id"] not in module_ids:
                continue
            repo_name = module["repo"]
            # 检查文件路径是否以模块路径开头
            for scanned_file in scanned_files:
                if scanned_file["repo"] != repo_name:
                    continue
                if any(scanned_file["file_path"].startswith(path) for path in module.get("paths", [])):
                    files.append(f"{repo_name}:{scanned_file['file_path']}")
        return files[:8]

    # related_commits: 根据关键词查找相关的提交记录
    # 优先从 PostgreSQL 获取（如果启用）
    def related_commits(self, keywords: list[str]) -> list[dict]:
        if self.postgres.enabled:
            commits = self._postgres_commits(keywords)
            if commits:
                return commits
        # 从内存中的提交列表匹配
        matched = []
        for commit in self.commits:
            haystack = f"{commit['message']} {' '.join(commit.get('keywords', []))}".lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                matched.append(commit)
        return matched[:5]

    # ========== PostgreSQL 查询方法 ==========

    # 从 PostgreSQL 获取模块列表
    def _postgres_modules(self) -> list[dict]:
        self.postgres.ensure_schema()
        with self.postgres.connect() as connection:
            rows = connection.execute(
                """
                select m.id, r.name as repo, m.name, m.directory_paths as paths,
                       m.keywords, m.keywords as tags, m.typical_questions,
                       m.key_entry_files, m.versions, m.chips, m.frameworks, m.description
                from modules m
                join repos r on r.id = m.repo_id
                order by m.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    # 从 PostgreSQL 获取文件列表
    def _postgres_files(self) -> list[dict]:
        self.postgres.ensure_schema()
        with self.postgres.connect() as connection:
            rows = connection.execute(
                """
                select r.name as repo, f.file_path, f.language, f.size_bytes
                from files f
                join repos r on r.id = f.repo_id
                order by r.name, f.file_path
                """
            ).fetchall()
        return [dict(row) for row in rows]

    # 从 PostgreSQL 获取相关提交（支持关键词模糊匹配）
    def _postgres_commits(self, keywords: list[str]) -> list[dict]:
        self.postgres.ensure_schema()
        lowered = [keyword.lower() for keyword in keywords if keyword]
        if not lowered:
            return []
        patterns = [f"%{keyword}%" for keyword in lowered]
        with self.postgres.connect() as connection:
            rows = connection.execute(
                """
                select r.name as repo, c.hash, c.message, c.keywords, c.summary
                from commits c
                join repos r on r.id = c.repo_id
                where lower(c.message) like any(%s)
                   or exists (
                       select 1 from unnest(c.keywords) keyword
                       where lower(keyword) like any(%s)
                   )
                order by c.committed_at desc nulls last, c.id desc
                limit 5
                """,
                (patterns, patterns),
            ).fetchall()
        return [dict(row) for row in rows]
