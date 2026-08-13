from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=25)
    email: str = Field(min_length=3, max_length=99, pattern=r"^[^@\s]+@[^@\s]+$")


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
