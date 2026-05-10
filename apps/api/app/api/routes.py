# 请求/响应数据模型（Pydantic）
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse
# 依赖注入 ，获取各个服务实例
from app.services.dependencies import (
    get_architecture_summary,
    get_code_search_tool,
    get_diagnosis_service,
    get_evaluator,
    get_memory_store,
    get_repo_registry,
    get_repository_index,
)
# FastAPI 路由组，用于模块化管理
from fastapi import APIRouter, Query


router = APIRouter()

# 执行诊断，核心调用
@router.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    return get_diagnosis_service().diagnose(request)

# 获取仓库列表
@router.get("/repos")
def list_repos() -> list[dict]:
    return get_repo_registry().list_repos()

# 获取仓库文件列表
@router.get("/repos/files")
def list_repo_files() -> list[dict]:
    return get_repository_index().list_files()

# 代码搜索工具
@router.get("/tools/search-code")
def search_code(q: list[str] = Query(...), max_results: int = 20) -> dict:
    return {"matches": get_code_search_tool().search_code(q, max_results=max_results)}


# 获取模块列表
@router.get("/modules")
def list_modules() -> list[dict]:
    return get_repository_index().list_modules()

#获取模块详情
@router.get("/modules/{module_id}")
def get_module(module_id: str) -> dict:
    return get_repository_index().get_module(module_id)

# 查看记忆存储状态（短期/长期记忆数量）
@router.get("/memory/summary")
def memory_summary() -> dict:
    return get_memory_store().summary()

# 查看支持的评估指标
@router.get("/eval/summary")
def eval_summary() -> dict:
    return get_evaluator().summary()

# 查看系统架构设计文档
@router.get("/architecture")
def architecture() -> dict:
    return get_architecture_summary()
