"""Health check response models."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Process health as seen by deployment and monitoring tools."""

    status: Literal["ok"]
    version: str
    database: Literal["not_configured"]
