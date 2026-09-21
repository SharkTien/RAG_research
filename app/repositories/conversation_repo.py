import json
import logging
import uuid
from datetime import datetime
from app.core.database import DatabaseManager

logger = logging.getLogger("conversation_repo")

class ConversationRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def list_conversations(self, username: str = None) -> list[dict]:
        query = """
            SELECT c.id, c.title, c.username, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
        """
        params = []
        if username:
            query += " WHERE c.username = %s"
            params.append(username)
        query += " GROUP BY c.id ORDER BY c.updated_at DESC"

        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "username": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": row[4].isoformat() if row[4] else None,
                    "message_count": row[5] or 0
                }
                for row in rows
            ]

    def create_conversation(self, title: str, username: str = "admin", conv_id: str = None) -> dict:
        cid = uuid.UUID(conv_id) if conv_id else uuid.uuid4()
        with self.db.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO conversations (id, title, username, created_at, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (cid, title.strip() or "Hội thoại mới", username)
                )
                conn.commit()
                return {
                    "id": str(cid),
                    "title": title.strip() or "Hội thoại mới",
                    "username": username,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "message_count": 0
                }
            except Exception as e:
                conn.rollback()
                logger.error("Lỗi khi tạo cuộc trò chuyện: %s", e, exc_info=True)
                raise

    def get_conversation(self, conv_id: str) -> dict | None:
        try:
            cid = uuid.UUID(conv_id)
        except (ValueError, TypeError):
            return None

        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, username, created_at, updated_at
                FROM conversations
                WHERE id = %s
                """,
                (cid,)
            ).fetchone()
            if not row:
                return None
            return {
                "id": str(row[0]),
                "title": row[1],
                "username": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": row[4].isoformat() if row[4] else None,
            }

    def update_title(self, conv_id: str, title: str) -> bool:
        try:
            cid = uuid.UUID(conv_id)
        except (ValueError, TypeError):
            return False

        with self.db.connect() as conn:
            try:
                conn.execute(
                    """
                    UPDATE conversations
                    SET title = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (title.strip(), cid)
                )
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error("Lỗi cập nhật tiêu đề hội thoại: %s", e)
                return False

    def delete_conversation(self, conv_id: str) -> bool:
        try:
            cid = uuid.UUID(conv_id)
        except (ValueError, TypeError):
            return False

        with self.db.connect() as conn:
            try:
                conn.execute("DELETE FROM conversations WHERE id = %s", (cid,))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error("Lỗi xóa hội thoại: %s", e)
                return False

    def get_messages(self, conv_id: str) -> list[dict]:
        try:
            cid = uuid.UUID(conv_id)
        except (ValueError, TypeError):
            return []

        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, sources, retrieved_chunks, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                """,
                (cid,)
            ).fetchall()

            messages = []
            for r in rows:
                sources = r[4]
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except Exception:
                        sources = []
                elif sources is None:
                    sources = []

                retrieved = r[5]
                if isinstance(retrieved, str):
                    try:
                        retrieved = json.loads(retrieved)
                    except Exception:
                        retrieved = []
                elif retrieved is None:
                    retrieved = []

                messages.append({
                    "id": str(r[0]),
                    "conversation_id": str(r[1]),
                    "role": r[2],
                    "content": r[3],
                    "sources": sources,
                    "retrieved_chunks": retrieved,
                    "created_at": r[6].isoformat() if r[6] else None
                })
            return messages

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        sources: list = None,
        retrieved_chunks: list = None
    ) -> dict:
        cid = uuid.UUID(conv_id)
        mid = uuid.uuid4()
        sources_json = json.dumps(sources or [], ensure_ascii=False)
        chunks_json = json.dumps(retrieved_chunks or [], ensure_ascii=False)

        with self.db.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, sources, retrieved_chunks, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (mid, cid, role, content, sources_json, chunks_json)
                )
                conn.execute(
                    """
                    UPDATE conversations
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (cid,)
                )
                conn.commit()
                return {
                    "id": str(mid),
                    "conversation_id": str(cid),
                    "role": role,
                    "content": content,
                    "sources": sources or [],
                    "retrieved_chunks": retrieved_chunks or [],
                    "created_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                conn.rollback()
                logger.error("Lỗi khi thêm tin nhắn vào hội thoại: %s", e, exc_info=True)
                raise
