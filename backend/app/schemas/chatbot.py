from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict]
    row_count: int
