from contextlib import contextmanager
from typing import Iterator

from app.core.config import get_settings

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional production dependency
    psycopg = None
    dict_row = None


class PostgresStore:
    """Small synchronous PostgreSQL gateway for repo metadata and feedback."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enable_postgres and psycopg)

    @contextmanager
    def connect(self) -> Iterator:
        if not self.enabled:
            raise RuntimeError("PostgreSQL is disabled or psycopg is not installed")
        with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as connection:
            yield connection

    def ensure_schema(self) -> None:
        if not self.enabled:
            return
        with self.connect() as connection:
            connection.execute(
                """
                create table if not exists repos (
                    id bigserial primary key,
                    name text not null unique,
                    path text not null,
                    repo_type text not null default 'code',
                    default_branch text not null default 'main',
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );

                create table if not exists files (
                    id bigserial primary key,
                    repo_id bigint not null references repos(id) on delete cascade,
                    file_path text not null,
                    language text not null default 'text',
                    suffix text not null default '',
                    size_bytes bigint not null default 0,
                    updated_at timestamptz not null default now(),
                    unique(repo_id, file_path)
                );

                create table if not exists commits (
                    id bigserial primary key,
                    repo_id bigint not null references repos(id) on delete cascade,
                    hash text not null,
                    message text not null,
                    author text,
                    committed_at timestamptz,
                    keywords text[] not null default '{}',
                    summary text,
                    unique(repo_id, hash)
                );

                create table if not exists modules (
                    id text primary key,
                    repo_id bigint not null references repos(id) on delete cascade,
                    name text not null,
                    directory_paths text[] not null default '{}',
                    keywords text[] not null default '{}',
                    typical_questions text[] not null default '{}',
                    key_entry_files text[] not null default '{}',
                    versions text[] not null default '{}',
                    chips text[] not null default '{}',
                    frameworks text[] not null default '{}',
                    description text not null default '',
                    updated_at timestamptz not null default now()
                );

                create table if not exists ingestion_runs (
                    id bigserial primary key,
                    status text not null,
                    started_at timestamptz not null default now(),
                    finished_at timestamptz,
                    repos_count integer not null default 0,
                    files_count integer not null default 0,
                    commits_count integer not null default 0,
                    modules_count integer not null default 0,
                    error text
                );

                create table if not exists feedback (
                    id bigserial primary key,
                    session_id text,
                    hit boolean not null,
                    correct_module text,
                    correct_file text,
                    final_conclusion text,
                    note text,
                    created_at timestamptz not null default now()
                );
                """
            )
            connection.commit()
