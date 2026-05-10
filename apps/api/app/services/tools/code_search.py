# CodeSearchTool: 代码搜索工具
# 基于 ripgrep (rg) 在注册仓库中搜索代码
# 支持多关键词搜索、文件过滤、目录忽略等功能
import json
import subprocess
from pathlib import Path

from app.services.indexing.repo_registry import RepoRegistry


class CodeSearchTool:
    """ripgrep based code search over registered repos."""

    def __init__(self, repo_registry: RepoRegistry) -> None:
        self.repo_registry = repo_registry
        # 默认搜索的文件后缀
        self.default_suffixes = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".py", ".md", ".txt"}
        # 默认忽略的目录
        self.default_ignore_dirs = {".git", "build", "dist", "node_modules", ".venv", "__pycache__"}

    # search_code: 在仓库中搜索代码
    # 参数:
    #   - queries: 搜索关键词列表
    #   - max_results: 最大结果数
    #   - repo: 指定仓库名称（可选）
    #   - path_prefix: 文件路径前缀（可选）
    #   - file_path: 精确文件路径（可选）
    #   - file_suffixes: 文件后缀过滤列表（可选）
    #   - timeout_seconds: 超时秒数
    #   - ignore_dirs: 忽略的目录列表（可选）
    # 返回: 匹配结果列表，每项包含 repo, file_path, line, text, hit_terms, context
    def search_code(
        self,
        queries: list[str],
        max_results: int = 20,
        repo: str | None = None,
        path_prefix: str | None = None,
        file_path: str | None = None,
        file_suffixes: list[str] | None = None,
        timeout_seconds: float = 3.0,
        ignore_dirs: list[str] | None = None,
    ) -> list[dict]:
        # 过滤空关键词
        normalized_queries = [query.strip() for query in queries if query.strip()]
        if not normalized_queries:
            return []

        # 处理文件后缀和忽略目录
        suffixes = self._normalize_suffixes(file_suffixes)
        skipped_dirs = set(ignore_dirs or self.default_ignore_dirs)
        matches: list[dict] = []

        # 遍历所有注册的仓库进行搜索
        for repo_config in self.repo_registry.repos:
            # 如果指定了仓库名，跳过其他仓库
            if repo and repo_config.name != repo:
                continue
            if not repo_config.path.exists():
                continue
            # 在当前仓库中搜索
            repo_matches = self._search_repo(
                repo_name=repo_config.name,
                repo_path=repo_config.path,
                queries=normalized_queries,
                max_results=max_results - len(matches),
                path_prefix=path_prefix,
                file_path=file_path,
                suffixes=suffixes,
                timeout_seconds=timeout_seconds,
                ignore_dirs=skipped_dirs,
            )
            matches.extend(repo_matches)
            # 达到最大结果数，停止搜索
            if len(matches) >= max_results:
                return matches[:max_results]
        return matches

    # 读取文件的指定行范围
    def read_file_slice(self, repo_name: str, file_path: str, start_line: int, end_line: int) -> dict:
        repo = self.repo_registry.get_repo(repo_name)
        target = (repo.path / file_path).resolve()
        # 安全检查：确保文件路径在仓库目录内
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

    # _search_repo: 在单个仓库中执行 ripgrep 搜索
    def _search_repo(
        self,
        repo_name: str,
        repo_path: Path,
        queries: list[str],
        max_results: int,
        path_prefix: str | None,
        file_path: str | None,
        suffixes: set[str],
        timeout_seconds: float,
        ignore_dirs: set[str],
    ) -> list[dict]:
        if max_results <= 0:
            return []

        # 构建 ripgrep 命令
        command = [
            "rg",                    # ripgrep 命令
            "--json",                # JSON 输出格式
            "--line-number",         # 显示行号
            "--no-heading",          # 每个文件的结果不重复显示文件名
            "--ignore-case",          # 忽略大小写
            "--color", "never",      # 禁用颜色
            "--max-count", str(max_results),  # 最大匹配数
        ]
        # 添加忽略目录的 glob 模式
        for ignored in sorted(ignore_dirs):
            command.extend(["--glob", f"!**/{ignored}/**"])
        # 添加文件后缀过滤
        for suffix in sorted(suffixes):
            command.extend(["--glob", f"*{suffix}"])

        # 多关键词用 OR 正则拼接，让 ripgrep 一次扫描仓库
        command.extend(["-e", "|".join(self._escape_rg_regex(query) for query in queries)])

        # 确定搜索根目录
        search_root = repo_path
        requested_path = file_path or path_prefix
        if requested_path:
            candidate = (repo_path / requested_path).resolve()
            if repo_path in candidate.parents or candidate == repo_path:
                search_root = candidate
        command.append(str(search_root))

        # 执行 ripgrep 命令
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            # ripgrep 未安装
            raise RuntimeError("ripgrep (`rg`) is required for production code search") from exc
        except subprocess.TimeoutExpired:
            # 搜索超时
            return []

        # ripgrep 返回码 0 表示找到匹配，1 表示没找到匹配，都是正常情况
        if completed.returncode not in {0, 1}:
            return []

        # 解析 JSON 输出
        matches: list[dict] = []
        for raw_line in completed.stdout.splitlines():
            if len(matches) >= max_results:
                break
            parsed = self._parse_rg_match(raw_line, repo_name, repo_path, queries)
            if parsed:
                matches.append(parsed)
        return matches

    # _parse_rg_match: 解析 ripgrep 的 JSON 输出行
    def _parse_rg_match(self, raw_line: str, repo_name: str, repo_path: Path, queries: list[str]) -> dict | None:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            return None
        # 只处理匹配类型的结果
        if payload.get("type") != "match":
            return None

        data = payload["data"]
        absolute_path = Path(data["path"]["text"]).resolve()
        # 安全检查
        if repo_path not in absolute_path.parents and absolute_path != repo_path:
            return None

        file_path = absolute_path.relative_to(repo_path).as_posix()
        text = data["lines"]["text"].rstrip("\n")
        lower_text = text.lower()
        # 找出命中的关键词
        hit_terms = [query for query in queries if query.lower() in lower_text]
        line_number = int(data["line_number"])
        lines = self._read_lines(absolute_path)
        return {
            "repo": repo_name,
            "file_path": file_path,
            "line": line_number,
            "text": text.strip(),
            "hit_terms": hit_terms,
            # 上下文：匹配行及其上下各一行
            "context": self._context(lines, line_number),
        }

    # 规范化文件后缀格式（确保以 . 开头）
    def _normalize_suffixes(self, file_suffixes: list[str] | None) -> set[str]:
        if not file_suffixes:
            return set(self.default_suffixes)
        return {suffix if suffix.startswith(".") else f".{suffix}" for suffix in file_suffixes}

    # 转义 ripgrep 正则表达式的特殊字符
    def _escape_rg_regex(self, value: str) -> str:
        special = set(r"\.^$*+?{}[]|()")
        return "".join(f"\\{char}" if char in special else char for char in value)

    # 读取文件所有行（支持 UTF-8 和 Latin-1 编码）
    def _read_lines(self, path: Path) -> list[str]:
        try:
            return path.read_text(encoding="utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1").splitlines(keepends=True)

    # 获取上下文字符串（当前行及其上下各一行）
    def _context(self, lines: list[str], line_number: int) -> list[str]:
        start = max(1, line_number - 1)
        end = min(len(lines), line_number + 1)
        return [line.rstrip("\n") for line in lines[start - 1 : end]]
