# DCU Agent Demo

一个面向 DCU 生态软件问题定位场景的最小可扩展 Demo。

当前版本目标：
- 跑通 `问题描述 -> 问题解析 -> 模块召回 -> 相关文件/提交 -> 诊断建议`
- 预留 RAG、记忆、工具调用、MCP、多 Agent、评估、Redis、Milvus、Docker 化接口
- 使用本地样例数据，便于快速启动和后续替换为真实仓库/真实数据

## 目录

- `apps/api`: FastAPI 后端
- `frontend`: 最小静态页面
- `infra/docker`: Dockerfile
- `docs`: 补充说明

## 当前能力

- `FastAPI` 服务
- 最小诊断工作流
- 模块、文件、提交、案例样例数据
- 短期记忆/长期记忆接口占位
- RAG 检索接口占位
- Tool Registry
- MCP Gateway 占位
- 多 Agent 编排占位
- 评估接口占位
- `docker-compose` 集成 `Milvus`、`Redis`、`Postgres`

## 快速启动

### 方式 1：本地 Python

1. 进入后端目录
2. 安装依赖
3. 启动服务

```powershell
cd C:\Users\Admin\Desktop\dcu-agent-demo\apps\api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开：
- API 文档：`http://127.0.0.1:8000/docs`
- Demo 页面：`http://127.0.0.1:8000/`

### 方式 2：Docker Compose

```powershell
cd C:\Users\Admin\Desktop\dcu-agent-demo
docker compose up --build
```

## 关键接口

- `GET /health`
- `GET /api/v1/modules`
- `GET /api/v1/modules/{module_id}`
- `POST /api/v1/diagnose`
- `GET /api/v1/memory/summary`
- `GET /api/v1/eval/summary`
- `GET /api/v1/architecture`

## 后续替换建议

- 把 `app/data/*.json` 替换成真实代码索引产物
- 把 `SampleRagRetriever` 替换成 Milvus 检索实现
- 把 `InMemoryMemoryStore` 替换成 Redis + Postgres
- 把 `SimpleAgentOrchestrator` 迁移到 LangGraph
- 把 `StaticMcpGateway` 替换成真实 MCP server/client
