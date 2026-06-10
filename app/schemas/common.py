from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str