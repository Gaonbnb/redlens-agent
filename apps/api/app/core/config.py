import os
from dataclasses import dataclass
from functools import lru_cache


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str          # 应用名称
    app_env: str           # 运行环境 (local/test/prod)
    app_host: str          # 服务绑定地址
    app_port: int          # 服务端口
    redis_url: str         # Redis 连接地址
    postgres_dsn: str      # PostgreSQL 连接字符串
    milvus_host: str       # Milvus 向量数据库主机
    milvus_port: int       # Milvus 端口
    enable_milvus: bool    # 是否启用 Milvus
    enable_redis: bool     # 是否启用 Redis
    enable_postgres: bool  # 是否启用 PostgreSQL

# @lru_cache 装饰器确保配置只加载一次
@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "DCU Agent Demo"),
        app_env=os.getenv("APP_ENV", "local"),
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        postgres_dsn=os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/dcu_agent"),
        milvus_host=os.getenv("MILVUS_HOST", "localhost"),
        milvus_port=int(os.getenv("MILVUS_PORT", "19530")),
        enable_milvus=_as_bool(os.getenv("ENABLE_MILVUS")),
        enable_redis=_as_bool(os.getenv("ENABLE_REDIS")),
        enable_postgres=_as_bool(os.getenv("ENABLE_POSTGRES")),
    )
