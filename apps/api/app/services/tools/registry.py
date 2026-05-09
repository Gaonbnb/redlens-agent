# 作用 ：管理可用的诊断工具清单
class ToolRegistry:
    def __init__(self) -> None:
        self._tools = [
            {"name": "search_code", "kind": "code", "status": "planned"},
            {"name": "search_cases", "kind": "rag", "status": "active-placeholder"},
            {"name": "search_commits", "kind": "git", "status": "planned"},
            {"name": "trace_module", "kind": "code", "status": "planned"},
            {"name": "run_sql", "kind": "data", "status": "planned"},
        ]

    def list_tools(self) -> list[dict]:
        return self._tools
