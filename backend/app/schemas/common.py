from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error_code: str = Field(..., description="Machine readable error code")
    message: str = Field(..., description="Human readable error message")
    details: list[str] | None = Field(default=None, description="Optional extra error details")
