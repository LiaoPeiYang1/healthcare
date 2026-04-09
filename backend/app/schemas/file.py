from pydantic import BaseModel, Field


class FileCheckRequest(BaseModel):
    file_hash: str = Field(min_length=8)
    filename: str = Field(min_length=1)
    file_size: int = Field(gt=0)
    total_chunks: int = Field(gt=0)


class FileCheckResponse(BaseModel):
    exists: bool
    file_id: str | None = None


class FileMergeRequest(BaseModel):
    file_hash: str
    filename: str
    total_chunks: int = Field(gt=0)
    mime_type: str


class FileMergeResponse(BaseModel):
    file_id: str
