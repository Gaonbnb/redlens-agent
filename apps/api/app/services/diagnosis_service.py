# 诊断服务，连接编排器和记忆存储
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse
from app.services.agents.orchestrator import SimpleAgentOrchestrator
from app.services.memory.store import InMemoryMemoryStore


class DiagnosisService:
    def __init__(self, orchestrator: SimpleAgentOrchestrator, memory_store: InMemoryMemoryStore) -> None:
        self.orchestrator = orchestrator
        self.memory_store = memory_store

    def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        result = self.orchestrator.run(request) # 执行诊断
        self.memory_store.record_interaction(request, result) # 记录到记忆
        return result
