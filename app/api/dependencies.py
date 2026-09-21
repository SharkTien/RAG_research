from fastapi import Request, HTTPException, status, Depends
import jwt
from app.core.config import JWT_SECRET_KEY, ALGORITHM
from app.core.database import DatabaseManager
from app.core.storage import StorageManager
from app.repositories.document_repo import DocumentRepository
from app.services.document_service import DocumentService
from app.services.extract_service import ExtractService

def get_current_user(request: Request) -> str:
    # 1. Get JWT from cookie, Authorization header, or query param
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        token = request.query_params.get("token")
        
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Không tìm thấy phiên đăng nhập")
        
    try:
        # 2. Verify JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        csrf_in_token: str = payload.get("csrf")
        if username is None or csrf_in_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")
            
        # 3. Verify CSRF for state-changing requests
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            csrf_header = request.headers.get("x-csrf-token")
            if not csrf_header or csrf_header != csrf_in_token:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Lỗi xác thực CSRF")
                
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")

# Dependency Injection Providers
def get_database() -> DatabaseManager:
    return DatabaseManager()

def get_storage() -> StorageManager:
    return StorageManager()

def get_document_repo(db: DatabaseManager = Depends(get_database)) -> DocumentRepository:
    return DocumentRepository(db)

def get_document_service(
    repo: DocumentRepository = Depends(get_document_repo),
    storage: StorageManager = Depends(get_storage)
) -> DocumentService:
    return DocumentService(repo, storage)

def get_extract_service(
    repo: DocumentRepository = Depends(get_document_repo),
    storage: StorageManager = Depends(get_storage)
) -> ExtractService:
    return ExtractService(repo, storage)

from app.repositories.chunk_repo import ChunkRepository
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.rag_service import RagService

def get_chunk_repo(db: DatabaseManager = Depends(get_database)) -> ChunkRepository:
    return ChunkRepository(db)

def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()

def get_retrieval_service(
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    embedder: EmbeddingService = Depends(get_embedding_service)
) -> RetrievalService:
    return RetrievalService(chunk_repo, embedder)

def get_rag_service(
    retriever: RetrievalService = Depends(get_retrieval_service)
) -> RagService:
    return RagService(retriever)

from app.repositories.conversation_repo import ConversationRepository

def get_conversation_repo(db: DatabaseManager = Depends(get_database)) -> ConversationRepository:
    return ConversationRepository(db)

