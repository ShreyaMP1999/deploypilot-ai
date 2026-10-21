from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequestInput(StrictModel):
    text: str = Field(min_length=5, max_length=4000)
    record_id: str = Field(min_length=1, max_length=80)
    amount_cents: int | None = Field(default=None, gt=0, le=100_000_000, strict=True)
    payment_method: Literal["original", "other"] = "original"


class Recommendation(StrictModel):
    classification: Literal["refund", "documentation", "security", "other"]
    summary: str = Field(max_length=1200)
    response_draft: str = Field(max_length=2000)
    uncertain: bool


class LoginInput(StrictModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(max_length=80)


class SwitchInput(StrictModel):
    tenant_id: str = Field(max_length=80)


class ApprovalInput(StrictModel):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=1000)
