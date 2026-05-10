from app.schemas.diagnosis import FeedbackRequest
from app.services.storage.postgres import PostgresStore


class FeedbackStore:
    def __init__(self, postgres: PostgresStore) -> None:
        self.postgres = postgres
        self._fallback: list[dict] = []

    def record(self, request: FeedbackRequest) -> int | None:
        if not self.postgres.enabled:
            self._fallback.append(request.model_dump())
            return None

        self.postgres.ensure_schema()
        with self.postgres.connect() as connection:
            row = connection.execute(
                """
                insert into feedback(
                    session_id, hit, correct_module, correct_file, final_conclusion, note
                )
                values (%s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    request.session_id,
                    request.hit,
                    request.correct_module,
                    request.correct_file,
                    request.final_conclusion,
                    request.note,
                ),
            ).fetchone()
            connection.commit()
            return row["id"]

    def summary(self) -> dict:
        if not self.postgres.enabled:
            return {"backend": "memory", "count": len(self._fallback)}
        self.postgres.ensure_schema()
        with self.postgres.connect() as connection:
            row = connection.execute("select count(*) as count from feedback").fetchone()
            return {"backend": "postgres", "count": row["count"]}
