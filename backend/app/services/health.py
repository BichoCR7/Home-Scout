"""Health/readiness orchestration kept separate from HTTP routes."""

from sqlalchemy.orm import Session

from app.data_access.health import HealthRepository


class HealthService:
    def __init__(self, repository: HealthRepository | None = None) -> None:
        self._repository = repository or HealthRepository()

    def database_is_ready(self, session: Session) -> bool:
        return self._repository.is_database_available(session)
