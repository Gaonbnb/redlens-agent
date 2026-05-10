# diagnosis.py: 诊断相关的数据模型定义
# 使用 Pydantic 定义请求/响应数据结构
from pydantic import BaseModel, Field


# ========== 请求模型 ==========

# DiagnosisRequest: 前端发送的诊断请求
# 包含问题标题、描述、版本、框架、芯片等信息
class DiagnosisRequest(BaseModel):
    title: str = Field(..., description="问题标题")
    description: str = Field(..., description="问题详细描述")
    version: str | None = Field(None, description="软件/驱动版本")
    framework: str | None = Field(None, description="框架类型，如 PyTorch")
    chip: str | None = Field(None, description="芯片型号，如 DCU-X")


# ========== 问题理解模型 ==========

# ProblemUnderstanding: 问题理解结果
# 包含识别的领域、症状、缺失信息、关键词
class ProblemUnderstanding(BaseModel):
    domain: str          # 问题领域（runtime_init/framework_adaptation/performance/general）
    symptoms: list[str]  # 识别到的症状列表
    missing_info: list[str]  # 缺失的信息列表
    keywords: list[str]  # 提取的关键词列表


# ========== 候选模块模型 ==========

# CandidateModule: 候选模块
# 表示一个可能被问题涉及的代码模块
class CandidateModule(BaseModel):
    name: str    # 模块名称
    score: float  # 匹配分数（0-1）
    reason: str  # 匹配原因说明


# ========== 代码匹配模型 ==========

# CodeMatch: 代码匹配结果
# 由 ripgrep 结构化解析得到的代码命中
class CodeMatch(BaseModel):
    repo: str          # 仓库名称
    file_path: str     # 文件路径
    line: int          # 行号
    text: str          # 匹配的代码文本
    hit_terms: list[str]  # 命中的关键词列表
    context: list[str]    # 上下文代码行


# ========== 相关提交模型 ==========

# RelatedCommit: 相关提交记录
class RelatedCommit(BaseModel):
    hash: str    # 提交 hash
    message: str  # 提交消息


# ========== 统一证据项模型 ==========

# EvidenceItem: 统一证据项
# 覆盖模块、代码、提交、案例等多种证据来源
class EvidenceItem(BaseModel):
    source_type: str  # 证据来源类型："module" | "code" | "commit" | "case"
    repo: str | None = None  # 仓库名称
    file_path: str | None = None  # 文件路径
    line: int | None = None  # 行号
    symbol_name: str | None = None  # 符号名称（如函数名）
    commit_hash: str | None = None  # 提交 hash
    case_id: str | None = None  # 案例 ID
    module_name: str | None = None  # 模块名称
    score: float = 0.0  # 证据分数
    reason: str  # 匹配原因说明
    preview: str  # 预览文本（简短描述）
    metadata: dict = Field(default_factory=dict)  # 额外元数据


# ========== 响应模型 ==========

# DiagnosisResponse: 后端返回的诊断结果
class DiagnosisResponse(BaseModel):
    problem_understanding: ProblemUnderstanding  # 问题理解结果
    candidate_modules: list[CandidateModule]     # 候选模块列表
    related_files: list[str]                    # 相关文件路径列表
    code_matches: list[CodeMatch] = Field(default_factory=list)  # 代码匹配结果
    related_commits: list[RelatedCommit]        # 相关提交列表
    evidence_items: list[EvidenceItem] = Field(default_factory=list)  # 统一证据项
    suggestions: list[str]                     # 排查建议列表
    debug_context: dict                         # 调试上下文信息


# ========== 用户反馈模型 ==========

# FeedbackRequest: 用户反馈请求
# 用于用户标记诊断结果是否正确，帮助改进长期记忆和评估
class FeedbackRequest(BaseModel):
    session_id: str | None = None  # 会话 ID
    hit: bool  # 诊断是否命中
    correct_module: str | None = None  # 正确模块
    correct_file: str | None = None  # 正确文件
    final_conclusion: str | None = None  # 最终结论
    note: str | None = None  # 备注


# FeedbackResponse: 反馈写入结果
class FeedbackResponse(BaseModel):
    status: str  # 状态（"recorded" 表示成功）
    feedback_id: int | None = None  # 反馈记录 ID


# ========== Ingestion 模型 ==========

# IngestionResponse: 仓库索引构建结果
# 记录 ingestion 执行后的统计信息
class IngestionResponse(BaseModel):
    status: str  # 执行状态
    run_id: int  # 运行 ID
    repos: int   # 处理的仓库数量
    files: int   # 索引的文件数量
    commits: int  # 索引的提交数量
    modules: int  # 索引的模块数量
