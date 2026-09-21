import psycopg
from contextlib import contextmanager
from app.core.config import DATABASE_URL

class DatabaseManager:
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url

    @contextmanager
    def connect(self):
        with psycopg.connect(self.db_url) as conn:
            yield conn

    def init_db(self):
        try:
            with self.connect() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id UUID PRIMARY KEY,
                        original_filename TEXT NOT NULL,
                        object_key TEXT NOT NULL,
                        content_type TEXT,
                        size_bytes BIGINT,
                        sha256 TEXT,
                        uploaded_by TEXT,
                        status TEXT DEFAULT 'uploaded',
                        error_message TEXT,
                        extracted_data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
                conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256 TEXT")
                # Add the persistent worker state to databases created by the MVP.
                conn.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_status_check")
                conn.execute("""
                    ALTER TABLE documents ADD CONSTRAINT documents_status_check
                    CHECK (status IN ('uploaded', 'queued', 'processing', 'processed', 'failed', 'cancelled'))
                """)
                conn.execute("UPDATE documents SET status = 'queued' WHERE status = 'uploaded'")

                # Khởi tạo pgvector extension và bảng document_chunks
                from app.core.config import EMBEDDING_DIM
                has_vector_ext = False
                try:
                    conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    has_vector_ext = True
                except Exception as ext_err:
                    print(f"Warning: pgvector extension could not be created: {ext_err}")

                if has_vector_ext:
                    conn.execute(f'''
                        CREATE TABLE IF NOT EXISTS document_chunks (
                            id UUID PRIMARY KEY,
                            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                            chunk_index INT NOT NULL,
                            content TEXT NOT NULL,
                            metadata JSONB,
                            embedding vector({EMBEDDING_DIM}),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(document_id);
                    ''')
                    conn.commit()
                    if int(EMBEDDING_DIM) <= 2000:
                        try:
                            with conn.transaction():
                                conn.execute('''
                                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
                                    ON document_chunks USING hnsw (embedding vector_cosine_ops);
                                ''')
                        except Exception as hnsw_err:
                            print(f"Notice: HNSW index creation skipped: {hnsw_err}")
                    else:
                        print(f"Notice: Exact vector search enabled for {EMBEDDING_DIM} dims (HNSW limit is 2000)")
                else:
                    conn.execute('''
                        CREATE TABLE IF NOT EXISTS document_chunks (
                            id UUID PRIMARY KEY,
                            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                            chunk_index INT NOT NULL,
                            content TEXT NOT NULL,
                            metadata JSONB,
                            embedding JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(document_id);
                    ''')

                # Create users table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'user'
                    )
                ''')
                
                # Only bootstrap an admin when an explicit password is supplied.
                from passlib.hash import argon2
                from app.core.config import ADMIN_PASSWORD, ADMIN_USERNAME
                admin_exists = conn.execute("SELECT id FROM users WHERE username = %s", (ADMIN_USERNAME,)).fetchone()
                if ADMIN_PASSWORD and not admin_exists:
                    conn.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                        (ADMIN_USERNAME, argon2.hash(ADMIN_PASSWORD), 'admin')
                    )
                    print(f"Bootstrap admin created: {ADMIN_USERNAME}")
                elif ADMIN_PASSWORD and admin_exists:
                    # Makes replacing the insecure MVP bootstrap password deterministic.
                    conn.execute(
                        "UPDATE users SET password_hash = %s, role = 'admin' WHERE username = %s",
                        (argon2.hash(ADMIN_PASSWORD), ADMIN_USERNAME),
                    )
                print("Database initialized")
        except Exception as e:
            print(f"Error initializing DB: {e}")
