# mcp占位
class StaticMcpGateway:
    def list_servers(self) -> list[dict]:
        return [
            {"name": "repo-mcp", "status": "planned"},
            {"name": "kb-mcp", "status": "planned"},
            {"name": "analytics-mcp", "status": "planned"},
        ]
