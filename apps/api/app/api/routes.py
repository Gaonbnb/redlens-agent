# API 路由定义文件
# 负责定义所有对外暴露的 REST API 端点
from app.schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestionResponse,
)
from app.services.dependencies import (
    get_architecture_summary,
    get_code_search_tool,
    get_diagnosis_service,
    get_evaluator,
    get_feedback_store,
    get_ingestion_service,
    get_memory_store,
    get_milvus_knowledge_store,
    get_repo_registry,
    get_repository_index,
)
from fastapi import APIRouter, Query

router = APIRouter()


# ========== 诊断相关接口 ==========

# POST /api/v1/diagnose
# 执行诊断，核心调用入口
# 接收问题描述，返回诊断结果（候选模块、代码证据、相关提交、排查建议）
@router.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    return get_diagnosis_service().diagnose(request)


# ========== 仓库相关接口 ==========

# GET /api/v1/repos
# 获取所有已注册的仓库列表
@router.get("/repos")
def list_repos() -> list[dict]:
    return get_repo_registry().list_repos()


# GET /api/v1/repos/files
# 获取所有仓库的文件列表
@router.get("/repos/files")
def list_repo_files() -> list[dict]:
    return get_repository_index().list_files()


# ========== 代码搜索相关接口 ==========

# GET /api/v1/tools/search-code
# 代码关键词搜索工具
# 参数:
#   - q: 搜索关键词列表（必填）
#   - max_results: 最大返回结果数（默认20）
#   - repo: 指定仓库名称（可选）
#   - path_prefix: 文件路径前缀过滤（可选）
#   - file_path: 精确文件路径（可选）
#   - suffix: 文件后缀过滤列表（可选，如 .cpp, .py）
#   - timeout_seconds: 搜索超时秒数（默认3.0）
#   - ignore_dir: 忽略的目录列表（可选）
@router.get("/tools/search-code")
def search_code(
    q: list[str] = Query(...),
    max_results: int = 20,
    repo: str | None = None,
    path_prefix: str | None = None,
    file_path: str | None = None,
    suffix: list[str] | None = Query(default=None),
    timeout_seconds: float = 3.0,
    ignore_dir: list[str] | None = Query(default=None),
) -> dict:
    return {
        "matches": get_code_search_tool().search_code(
            q,
            max_results=max_results,
            repo=repo,
            path_prefix=path_prefix,
            file_path=file_path,
            file_suffixes=suffix,
            timeout_seconds=timeout_seconds,
            ignore_dirs=ignore_dir,
        )
    }


# ========== 模块相关接口 ==========

# GET /api/v1/modules
# 获取所有模块列表
@router.get("/modules")
def list_modules() -> list[dict]:
    return get_repository_index().list_modules()


# GET /api/v1/modules/{module_id}
# 获取指定模块的详细信息
@router.get("/modules/{module_id}")
def get_module(module_id: str) -> dict:
    return get_repository_index().get_module(module_id)


# ========== 索引相关接口 ==========

# POST /api/v1/ingestion/run
# 执行仓库索引构建（扫描文件、加载提交、更新数据库）
@router.post("/ingestion/run", response_model=IngestionResponse)
def run_ingestion() -> IngestionResponse:
    return IngestionResponse(**get_ingestion_service().run())


# ========== 反馈相关接口 ==========

# POST /api/v1/feedback
# 记录用户对诊断结果的反馈（用于长期记忆和评估）
# 用于标记诊断是否命中、正确模块、最终结论等
@router.post("/feedback", response_model=FeedbackResponse)
def record_feedback(request: FeedbackRequest) -> FeedbackResponse:
    feedback_id = get_feedback_store().record(request)
    return FeedbackResponse(status="recorded", feedback_id=feedback_id)


# GET /api/v1/feedback/summary
# 获取反馈统计摘要
@router.get("/feedback/summary")
def feedback_summary() -> dict:
    return get_feedback_store().summary()


# ========== RAG/知识库相关接口 ==========

# GET /api/v1/rag/milvus/summary
# 获取 Milvus 向量知识库状态摘要
@router.get("/rag/milvus/summary")
def milvus_summary() -> dict:
    return get_milvus_knowledge_store().summary()


# ========== 记忆/评估/架构接口 ==========

# GET /api/v1/memory/summary
# 获取记忆存储状态（短期/长期记忆数量）
@router.get("/memory/summary")
def memory_summary() -> dict:
    return get_memory_store().summary()


# GET /api/v1/eval/summary
# 获取评估服务支持的指标列表
@router.get("/eval/summary")
def eval_summary() -> dict:
    return get_evaluator().summary()


# GET /api/v1/architecture
# 获取系统架构设计文档
@router.get("/architecture")
def architecture() -> dict:
    return get_architecture_summary()
