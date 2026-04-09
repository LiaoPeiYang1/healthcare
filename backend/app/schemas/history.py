from pydantic import BaseModel


class HistoryItemResponse(BaseModel):
    id: str
    task_type: str
    title: str
    status: str
    source_lang: str
    target_lang: str
    updated_at: str
    result_preview: str | None = None
    source_text: str | None = None
    translated_text: str | None = None
    file_id: str | None = None
    task_id: str | None = None
    result_file_id: str | None = None
    bilingual_file_id: str | None = None


class HistoryListResponse(BaseModel):
    items: list[HistoryItemResponse]
    total: int
    page: int
    page_size: int
