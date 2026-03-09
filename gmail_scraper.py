import base64
import json
import os
import re
import time
from datetime import datetime
from googleapiclient.discovery import build
from dotenv import load_dotenv
import anthropic
from db import get_db, fetchall, fetchone, execute, init_db
from gmail_auth import get_credentials

load_dotenv()

def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)

def _claude_call_with_retry(fn, retries=2):
    for attempt in range(retries + 1):
        try:
            return fn()
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            if attempt == retries:
                raise
            wait = 2 ** attempt
            print(f"  Claude API error ({e}), retrying in {wait}s...")
            time.sleep(wait)

def _parse_claude_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)

def extract_invoice_data(pdf_bytes, filename):
    client = anthropic.Anthropic()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    def call():
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": INVOICE_PROMPT,
                        },
                    ],
                }
            ],
        )

    message = _claude_call_with_retry(call)
    return _parse_claude_json(message.content[0].text)

def extract_invoice_from_email(subject, sender, date, body_text):
    client = anthropic.Anthropic()

    def call():
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze this email and return ONLY valid JSON.

Email Subject: {subject}
From: {sender}
Date: {date}

Email Body:
{body_text[:8000]}

{INVOICE_PROMPT}""",
                }
            ],
        )

    message = _claude_call_with_retry(call)
    return _parse_claude_json(message.content[0].text)

INVOICE_PROMPT = """Analyze this and return ONLY valid JSON.

First, determine if this is actually an invoice/bill/receipt (a document requesting or confirming payment for goods/services). It is NOT an invoice if it's a contract, proposal, waiver, case study, marketing material, presentation, newsletter, notification, or any non-billing document.

Return this exact JSON structure:
{
  "is_invoice": true/false,
  "confidence": 0-100,
  "vendor_name": "string or null",
  "amount": number or null,
  "currency": "string (3-letter code, default USD)",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "line_items": "brief description of what was billed, or null",
  "payment_status": "paid/unpaid/unknown"
}

Confidence scoring guide:
- 90-100: Clear invoice with vendor, amount, invoice number, and dates all present
- 70-89: Clearly an invoice but missing some fields (e.g. no due date or no invoice number)
- 50-69: Likely an invoice/receipt but key fields are ambiguous or hard to read
- 20-49: Might be billing-related but unclear (e.g. a payment confirmation email, statement)
- 0-19: Not an invoice (contract, proposal, waiver, marketing, etc.)

Payment status guide:
- "paid": Document says "PAID", "Payment received", "Balance due: $0.00", "Thank you for your payment", or is a payment receipt/confirmation
- "unpaid": Document shows an outstanding balance, says "Amount due", "Please remit payment", or has a future due date with no paid indicator
- "unknown": Cannot determine payment status from the document

For amount, use the total/grand total. If not an invoice, set all fields except is_invoice and confidence to null."""

def _strip_html(html):
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</td>', ' | ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _get_email_body(payload):
    if payload.get("mimeType") in ("text/plain", "text/html"):
        data = payload.get("body", {}).get("data")
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if payload["mimeType"] == "text/html":
                return _strip_html(decoded)
            return decoded

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data")
            if data:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                return _strip_html(decoded)

    for part in payload.get("parts", []):
        if part.get("mimeType", "").startswith("multipart/"):
            result = _get_email_body(part)
            if result:
                return result

    return None

def _has_pdf_attachment(payload):
    for part in _get_all_parts(payload):
        filename = part.get("filename", "")
        if filename.lower().endswith(".pdf") and part.get("body", {}).get("attachmentId"):
            return True
    return False

def fetch_new_invoices():
    service = get_gmail_service()
    conn = get_db()

    rows = fetchall(conn, "SELECT gmail_message_id, COALESCE(pdf_filename, '') as fname FROM invoices")
    existing_pairs = {(row["gmail_message_id"], row["fname"]) for row in rows}
    existing_msgs = {row["gmail_message_id"] for row in rows}

    # Two searches: PDFs and invoice-related emails
    queries = [
        "has:attachment filename:pdf",
        "subject:(invoice OR receipt OR billing OR \"payment due\" OR \"amount due\" OR \"balance due\" OR statement)",
    ]

    all_message_ids = {}
    for query in queries:
        results = service.users().messages().list(userId="me", q=query, maxResults=250).execute()
        for msg_info in results.get("messages", []):
            all_message_ids[msg_info["id"]] = True

    print(f"Found {len(all_message_ids)} candidate emails ({len(existing_msgs)} messages already in DB)")

    new_count = 0
    skipped = 0
    for msg_id in all_message_ids:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        date = headers.get("date", "")

        # First: try PDF attachments
        has_pdf = False
        for part in _get_all_parts(msg["payload"]):
            filename = part.get("filename", "")
            if not filename.lower().endswith(".pdf"):
                continue
            if not part.get("body", {}).get("attachmentId"):
                continue

            has_pdf = True
            if (msg_id, filename) in existing_pairs:
                skipped += 1
                continue

            att = service.users().messages().attachments().get(
                userId="me", messageId=msg_id, id=part["body"]["attachmentId"]
            ).execute()
            pdf_bytes = base64.urlsafe_b64decode(att["data"])

            try:
                invoice_data = extract_invoice_data(pdf_bytes, filename)
            except Exception as e:
                print(f"  Failed to parse PDF {filename}: {e}")
                continue

            saved = _save_invoice(conn, msg_id, msg, headers, invoice_data, "pdf", filename, pdf_bytes)
            if saved:
                new_count += 1
                conf = invoice_data.get("confidence", 0)
                label = "INVOICE" if invoice_data.get("is_invoice") else "NOT INVOICE"
                print(f"  [PDF {label} {conf}%] {filename} -> {invoice_data.get('vendor_name')} ${invoice_data.get('amount')}")

        # Second: if no PDF found, try email body
        if not has_pdf:
            if (msg_id, "") in existing_pairs:
                skipped += 1
                continue

            body_text = _get_email_body(msg["payload"])
            if not body_text or len(body_text.strip()) < 50:
                # Mark as seen so we don't re-process
                _save_empty(conn, msg_id, msg, headers)
                continue

            try:
                invoice_data = extract_invoice_from_email(subject, sender, date, body_text)
            except Exception as e:
                print(f"  Failed to parse email body [{subject[:50]}]: {e}")
                _save_empty(conn, msg_id, msg, headers)
                continue

            saved = _save_invoice(conn, msg_id, msg, headers, invoice_data, "email", None, None)
            if not saved:
                continue
            new_count += 1
            conf = invoice_data.get("confidence", 0)
            label = "INVOICE" if invoice_data.get("is_invoice") else "NOT INVOICE"
            print(f"  [EMAIL {label} {conf}%] {subject[:60]} -> {invoice_data.get('vendor_name')} ${invoice_data.get('amount')}")

    conn.close()
    print(f"\nDone. {new_count} new items processed, {skipped} already in DB.")
    return new_count

def _save_invoice(conn, msg_id, msg, headers, invoice_data, source_type, filename, pdf_bytes):
    existing = fetchone(conn,
        "SELECT id FROM invoices WHERE gmail_message_id = %s AND COALESCE(pdf_filename, '') = %s",
        (msg_id, filename or ""))
    if existing:
        return False
    execute(conn,
        """INSERT INTO invoices
        (gmail_message_id, gmail_thread_id, email_subject, email_from, email_date,
         vendor_name, amount, currency, invoice_number, invoice_date, due_date,
         line_items, pdf_filename, pdf_data, confidence, is_invoice, payment_status, source_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            msg_id,
            msg.get("threadId"),
            headers.get("subject", ""),
            headers.get("from", ""),
            headers.get("date", ""),
            invoice_data.get("vendor_name"),
            invoice_data.get("amount"),
            invoice_data.get("currency", "USD"),
            invoice_data.get("invoice_number"),
            invoice_data.get("invoice_date"),
            invoice_data.get("due_date"),
            invoice_data.get("line_items"),
            filename,
            pdf_bytes,
            invoice_data.get("confidence", 0),
            invoice_data.get("is_invoice", True),
            invoice_data.get("payment_status", "unknown"),
            source_type,
        ))
    conn.commit()
    return True

def _save_empty(conn, msg_id, msg, headers):
    existing = fetchone(conn,
        "SELECT id FROM invoices WHERE gmail_message_id = %s AND COALESCE(pdf_filename, '') = ''",
        (msg_id,))
    if existing:
        return
    execute(conn,
        """INSERT INTO invoices
        (gmail_message_id, gmail_thread_id, email_subject, email_from, email_date,
         confidence, is_invoice, source_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            msg_id,
            msg.get("threadId"),
            headers.get("subject", ""),
            headers.get("from", ""),
            headers.get("date", ""),
            0,
            False,
            "email",
        ))
    conn.commit()

def _get_all_parts(payload):
    parts = []
    if "parts" in payload:
        for p in payload["parts"]:
            parts.append(p)
            parts.extend(_get_all_parts(p))
    return parts

if __name__ == "__main__":
    init_db()
    fetch_new_invoices()
