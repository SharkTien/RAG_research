from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str

class ErrorResponse(BaseModel):
    detail: str
