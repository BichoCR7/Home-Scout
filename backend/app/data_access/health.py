"""Database connection probe used by API readiness checks."""

from sqlalchemy import text
from sqlalchemy.orm import Session


class HealthRepository:
    def is_database_available(self, session: Session) -> bool:
        return session.execute(text("SELECT 1")).scalar_one() == 1
