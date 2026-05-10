# 路径操作，处理前端文件目录
from pathlib import Path

from fastapi import FastAPI
# 返回静态文件（HTML）
from fastapi.responses import FileResponse
# 挂载静态文件服务
from fastapi.staticfiles import StaticFiles
# API 路由模块
from app.api.routes import router
# 配置模块
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

# 挂载静态文件服务
# __file__ = /root/.../apps/api/app/main.py
# Path(__file__).resolve().parents[3] = /root/.../apps/api  (向上3级)
# frontend_dir = /root/.../apps/api/frontend
def _find_frontend_dir() -> Path | None:
    frontend_dir = Path(__file__).resolve().parents[3] / "frontend"
    if not frontend_dir.exists():
        return None
    return frontend_dir

frontend_dir = _find_frontend_dir()
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# 定义根路由，返回 HTML 文件,include_in_schema=False 表示不显示在 API 文档中
@app.get("/", include_in_schema=False)
def index():
    if frontend_dir and (frontend_dir / "index.html").exists():
        return FileResponse(frontend_dir / "index.html")
    return HTMLResponse("<h1>DCU Agent Demo</h1><p>Open /docs for API documentation.</p>")


# 定义健康检查路由，返回应用状态
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

# 将 routes.py 中的所有路由注册到应用,添加 /api/v1 前缀统一版本管理
app.include_router(router, prefix="/api/v1")
