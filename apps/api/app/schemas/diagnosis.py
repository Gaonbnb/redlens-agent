# 诊断请求/响应数据模型（Pydantic）
from pydantic import BaseModel, Field

# 前端发送的诊断请求
class DiagnosisRequest(BaseModel):
    title: str = Field(..., description="Problem title")
    description: str = Field(..., description="Problem description")
    version: str | None = None
    framework: str | None = None
    chip: str | None = None

# 问题理解（领域、症状、关键词）
class ProblemUnderstanding(BaseModel):
    domain: str
    symptoms: list[str]
    missing_info: list[str]
    keywords: list[str]

# 候选模块（名称、分数、原因）
class CandidateModule(BaseModel):
    name: str
    score: float
    reason: str

class CodeMatch(BaseModel):
    repo: str
    file_path: str
    line: int
    text: str
    hit_terms: list[str]
    context: list[str]


# 相关提交（hash、message）
class RelatedCommit(BaseModel):
    hash: str
    message: str


# 后端返回的诊断结果
class DiagnosisResponse(BaseModel):
    problem_understanding: ProblemUnderstanding
    candidate_modules: list[CandidateModule]
    related_files: list[str]
    code_matches: list[CodeMatch] = Field(default_factory=list)
    related_commits: list[RelatedCommit]
    suggestions: list[str]
    debug_context: dict
