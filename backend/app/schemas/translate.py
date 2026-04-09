from pydantic import BaseModel, Field


class DetectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class DetectResponse(BaseModel):
    lang: str
    confidence: float


class TextTranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source_lang: str
    target_lang: str
    history_id: str | None = None


class TextTranslateResponse(BaseModel):
    task_id: str
    translated_text: str
    source_lang: str
    terminology_count: int
    history_id: str


class FileTranslateRequest(BaseModel):
    file_id: str
    source_lang: str
    target_lang: str
    history_id: str | None = None


class FileTranslateResponse(BaseModel):
    task_id: str
    status: str
    history_id: str


class FileTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result_file_id: str | None = None
    bilingual_file_id: str | None = None
    updated_at: str
    error: str | None = None
