from typing import List, Literal, Optional

from pydantic import BaseModel


class ChatHistoryItem(BaseModel):
    type: Literal["HUMAN_MESSAGE"] | Literal["AI_MESSAGE"]
    content: str


class FileContent(BaseModel):
    content: str
    file_name: str
    reference: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatHistoryItem]] = None
    files: Optional[List[FileContent]] = None


class LoadFileRequest(BaseModel):
    codebase_name: str
    file_path: str
    file_content: str
