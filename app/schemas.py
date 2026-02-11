"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import List

from pydantic import BaseModel, field_validator


# --- Request ---

class LinkCreate(BaseModel):
    target_url: str

    @field_validator("target_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("target_url cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("target_url must start with http:// or https://")
        return v.strip()


# --- Responses ---

class LinkResponse(BaseModel):
    short_code: str
    short_url: str
    target_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MonthlyBreakdown(BaseModel):
    month: str
    clicks: int


class LinkStats(BaseModel):
    short_code: str
    target_url: str
    total_clicks: int
    total_earnings: float
    monthly_breakdown: List[MonthlyBreakdown]


class StatsResponse(BaseModel):
    page: int
    limit: int
    total_links: int
    links: List[LinkStats]
