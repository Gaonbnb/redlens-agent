import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoConfig:
    name: str              # 仓库名称
    path: Path             # 仓库本地路径
    repo_type: str         # 仓库类型 (runtime/framework)
    default_branch: str    # 默认分支
    modules: list[dict]    # 模块列表


class RepoRegistry:
    """Loads repo registration and exposes a small read-only repo index."""

    def __init__(self) -> None:
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
        self.repos = self._load_repos()
    # repos.json → _load_repos() → 解析为 RepoConfig 对象列表 → 存储在 self.repos
    def _load_repos(self) -> list[RepoConfig]:
        config_path = self.data_dir / "repos.json"
        with config_path.open("r", encoding="utf-8") as file:
            raw_repos = json.load(file)

        repos = []
        for item in raw_repos:
            repo_path = Path(item["path"])
            if not repo_path.is_absolute():
                repo_path = self.data_dir / repo_path
            repos.append(
                RepoConfig(
                    name=item["name"],
                    path=repo_path.resolve(),
                    repo_type=item.get("repo_type", "code"),
                    default_branch=item.get("default_branch", "main"),
                    modules=item.get("modules", []),
                )
            )
        return repos
    # 获取所有仓库列表
    def list_repos(self) -> list[dict]:
        return [
            {
                "name": repo.name,
                "path": str(repo.path),
                "repo_type": repo.repo_type,
                "default_branch": repo.default_branch,
                "modules": repo.modules,
            }
            for repo in self.repos
        ]
    # 根据名称获取仓库
    def get_repo(self, name: str) -> RepoConfig:
        for repo in self.repos:
            if repo.name == name:
                return repo
        raise KeyError(f"Repo {name} not found")
    # 扫描所有仓库的文件
    def scan_files(self) -> list[dict]:
        files: list[dict] = []
        for repo in self.repos:
            for path in repo.path.rglob("*"): # 递归扫描所有文件
                if not path.is_file() or self._should_skip(path):
                    continue
                relative_path = path.relative_to(repo.path).as_posix()
                files.append(
                    {
                        "repo": repo.name,
                        "file_path": relative_path,
                        "language": self._language_for(path), # 根据后缀判断语言
                        "size_bytes": path.stat().st_size,
                    }
                )
        return files
    # 加载所有仓库的提交记录
    # 每个仓库的提交记录文件（COMMITS.json）在仓库根目录下
    def load_commits(self) -> list[dict]:
        commits: list[dict] = []
        for repo in self.repos:
            commit_file = repo.path / "COMMITS.json"
            if not commit_file.exists():
                continue
            with commit_file.open("r", encoding="utf-8") as file:
                for item in json.load(file):
                    commits.append({"repo": repo.name, **item})
        return commits
    # 加载所有仓库的模块卡片
    def module_cards(self) -> list[dict]:
        cards = []
        for repo in self.repos:
            for module in repo.modules:
                cards.append({"repo": repo.name, **module})
        return cards
    # 判断是否应该跳过扫描的文件或目录
    # 跳过 .git, build, dist, node_modules, .venv, __pycache__ 目录
    def _should_skip(self, path: Path) -> bool:
        skip_parts = {".git", "build", "dist", "node_modules", ".venv", "__pycache__"}
        return any(part in skip_parts for part in path.parts)
    # 根据文件路径缀判断语言
    def _language_for(self, path: Path) -> str:
        suffix = path.suffix.lower()
        return {
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".py": "python",
            ".md": "markdown",
            ".json": "json",
        }.get(suffix, "text")
