# RAG检索，扩展方向 ：接入 Milvus 向量数据库实现语义检索
class SampleRagRetriever:
    def __init__(self) -> None:
        self._cases = [
            {
                "id": "case-001",
                "title": "设备初始化失败导致 runtime 无法启动",
                "keywords": ["runtime", "init", "device"],
            },
            {
                "id": "case-002",
                "title": "PyTorch 适配场景下 operator loader 异常",
                "keywords": ["torch", "operator", "loader"],
            },
        ]
    # 基于关键词召回相关案例
    def retrieve(self, keywords: list[str]) -> list[dict]:
        results = []
        for case in self._cases:
            if any(keyword.lower() in " ".join(case["keywords"]).lower() for keyword in keywords):
                results.append(case)
        return results[:3]
