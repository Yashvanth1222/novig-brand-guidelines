import os
import psycopg2
import psycopg2.extras

def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "postgres"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", ""),
        )
    return conn

def fetchall(conn, query, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params or ())
        return cur.fetchall()

def fetchone(conn, query, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params or ())
        return cur.fetchone()

def execute(conn, query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())

def init_db():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                gmail_message_id TEXT,
                gmail_thread_id TEXT,
                email_subject TEXT,
                email_from TEXT,
                email_date TEXT,
                vendor_name TEXT,
                amount DOUBLE PRECISION,
                currency TEXT DEFAULT 'USD',
                invoice_number TEXT,
                invoice_date TEXT,
                due_date TEXT,
                line_items TEXT,
                pdf_filename TEXT,
                pdf_data BYTEA,
                ramp_bill_id TEXT,
                ramp_vendor_id TEXT,
                ramp_status TEXT DEFAULT 'not_uploaded',
                confidence INTEGER DEFAULT 0,
                is_invoice BOOLEAN DEFAULT TRUE,
                payment_status TEXT DEFAULT 'unknown',
                payment_confidence INTEGER DEFAULT 0,
                match_type TEXT,
                match_details TEXT,
                source_type TEXT DEFAULT 'pdf',
                ramp_transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'pdf'")
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS ramp_transaction_id TEXT")
        # Add unique constraint on message_id + filename to allow multiple PDFs per email
        cur.execute("ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_gmail_message_id_key")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_msg_file ON invoices (gmail_message_id, COALESCE(pdf_filename, ''))")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                id SERIAL PRIMARY KEY,
                last_history_id TEXT,
                last_sync_at TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendor_mapping (
                id SERIAL PRIMARY KEY,
                vendor_name_normalized TEXT UNIQUE,
                ramp_vendor_id TEXT,
                ramp_vendor_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_db()
    print("Database initialized.")
