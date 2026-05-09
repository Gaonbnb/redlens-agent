# 作用 ：保存诊断历史和知识
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse


class InMemoryMemoryStore:
    def __init__(self) -> None:
        # 短期记忆，最近10条诊断记录
        self._short_term: list[dict] = []
        # 长期记忆，初始知识库
        self._long_term: list[dict] = [
            {
                "type": "semantic",
                "title": "runtime_init_playbook",
                "content": "初始化失败优先检查版本匹配、入口调用、设备资源初始化。",
            }
        ]

    def record_interaction(self, request: DiagnosisRequest, response: DiagnosisResponse) -> None:
        self._short_term.append(
            {
                "title": request.title,
                "domain": response.problem_understanding.domain,
                "top_module": response.candidate_modules[0].name if response.candidate_modules else None,
            }
        )
        self._short_term = self._short_term[-10:]
    # 短期记忆，获取最近5条诊断记录
    def short_term_snapshot(self) -> list[dict]:
        return self._short_term[-5:]
    
    # 获取诊断记录摘要
    # 包含最近5条诊断记录、知识库类型统计
    def summary(self) -> dict:
        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "long_term_types": sorted({item["type"] for item in self._long_term}),
        }
