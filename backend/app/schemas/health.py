"""Health endpoint response contracts."""

from typing import Literal

from pydantic import BaseModel


class HealthLiveResponse(BaseModel):
    status: Literal["ok"]


class HealthReadyResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["ok"]
