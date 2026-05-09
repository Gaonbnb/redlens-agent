# 请求/响应数据模型（Pydantic）
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse
# 依赖注入 ，获取各个服务实例
from app.services.dependencies import (
    get_architecture_summary,
    get_diagnosis_service,
    get_evaluator,
    get_memory_store,
    get_repository_index,
)
# FastAPI 路由组，用于模块化管理
from fastapi import APIRouter


router = APIRouter()

# 执行诊断
@router.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    return get_diagnosis_service().diagnose(request)

# 获取模块列表
@router.get("/modules")
def list_modules() -> list[dict]:
    return get_repository_index().list_modules()

#获取模块详情
@router.get("/modules/{module_id}")
def get_module(module_id: str) -> dict:
    return get_repository_index().get_module(module_id)

# 记忆摘要
@router.get("/memory/summary")
def memory_summary() -> dict:
    return get_memory_store().summary()

# 评估摘要
@router.get("/eval/summary")
def eval_summary() -> dict:
    return get_evaluator().summary()

# 架构说明
@router.get("/architecture")
def architecture() -> dict:
    return get_architecture_summary()
