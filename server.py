import asyncio
import csv
import io
import json
import os
import base64
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from db import get_db, fetchall, fetchone, execute, init_db

load_dotenv()
init_db()

logger = logging.getLogger("invoice-automation")

def _refresh_ramp_token():
    client_id = os.environ.get("RAMP_CLIENT_ID")
    client_secret = os.environ.get("RAMP_CLIENT_SECRET")
    if not client_id or not client_secret:
        return
    try:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        resp = httpx.post(
            "https://api.ramp.com/developer/v1/token",
            headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": "bills:read bills:write vendors:read entities:read transactions:read reimbursements:read receipts:read users:read departments:read accounting:read"},
        )
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            os.environ["RAMP_ACCESS_TOKEN"] = token
            logger.info("Ramp token refreshed")
    except Exception as e:
        logger.error(f"Ramp token refresh failed: {e}")

def _run_gmail_scan():
    try:
        from gmail_scraper import fetch_new_invoices
        logger.info("Scheduled Gmail scan starting...")
        count = fetch_new_invoices()
        logger.info(f"Scheduled scan complete: {count} new invoices")
    except Exception as e:
        logger.error(f"Scheduled scan failed: {e}")

scheduler = BackgroundScheduler()
scan_interval = int(os.environ.get("SCAN_INTERVAL_HOURS", "6"))
scheduler.add_job(_run_gmail_scan, "interval", hours=scan_interval, id="gmail_scan")
scheduler.add_job(_refresh_ramp_token, "interval", days=7, id="ramp_token_refresh")

@asynccontextmanager
async def lifespan(app):
    scheduler.start()
    logger.info(f"Scheduler started: scanning Gmail every {scan_interval} hours")
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RAMP_BASE = "https://api.ramp.com"

@app.get("/api/invoices")
def list_invoices():
    conn = get_db()
    rows = fetchall(conn,
        """SELECT id, gmail_message_id, gmail_thread_id, email_subject, email_from, email_date,
           vendor_name, amount, currency, invoice_number, invoice_date, due_date,
           line_items, pdf_filename, ramp_bill_id, ramp_vendor_id, ramp_status,
           confidence, is_invoice, payment_status, payment_confidence, match_type, match_details,
           ramp_transaction_id, source_type, created_at
           FROM invoices ORDER BY is_invoice DESC, confidence DESC, created_at DESC""")
    conn.close()
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = str(r["created_at"])
    return rows

@app.get("/api/invoices/{invoice_id}/pdf")
def get_invoice_pdf(invoice_id: int):
    conn = get_db()
    row = fetchone(conn, "SELECT pdf_data, pdf_filename FROM invoices WHERE id = %s", (invoice_id,))
    conn.close()
    if not row or not row["pdf_data"]:
        raise HTTPException(404, "PDF not found")
    pdf_bytes = bytes(row["pdf_data"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{row["pdf_filename"]}"'},
    )

@app.get("/api/invoices/{invoice_id}/email-preview")
def get_invoice_email_preview(invoice_id: int):
    conn = get_db()
    row = fetchone(conn, """SELECT vendor_name, amount, currency, invoice_number, invoice_date, due_date,
        line_items, email_subject, email_from, email_date, payment_status, confidence,
        match_type, payment_confidence, match_details
        FROM invoices WHERE id = %s""", (invoice_id,))
    conn.close()
    if not row:
        raise HTTPException(404, "Invoice not found")

    details = []
    try:
        details = json.loads(row.get("match_details") or "[]")
    except Exception:
        pass

    from html import escape as h
    vendor = h(row.get('vendor_name') or 'Unknown Vendor')
    subject = h(row.get('email_subject') or 'No subject')
    currency = h(row.get('currency') or 'USD')
    inv_num = h(row.get('invoice_number') or '--')
    inv_date = h(row.get('invoice_date') or '--')
    due_date = h(row.get('due_date') or '--')
    line_items = h(str(row.get('line_items') or ''))
    email_from = h(row.get('email_from') or '--')
    email_date = h(row.get('email_date') or '--')
    pay_status = row.get('payment_status') or 'unknown'
    amount_str = f"${row['amount']:,.2f}" if row.get('amount') else '--'
    conf = row.get('confidence') or 0
    pay_conf = row.get("payment_confidence") or 0

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 24px; color: #1c1917; background: #fafaf9; }}
    .card {{ background: #fff; border: 1px solid #e7e5e4; border-radius: 10px; padding: 24px; max-width: 600px; margin: 0 auto; }}
    h2 {{ font-size: 18px; margin: 0 0 4px; }}
    .subtitle {{ font-size: 13px; color: #78716c; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .field {{ }}
    .field-label {{ font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #a8a29e; margin-bottom: 2px; }}
    .field-value {{ font-size: 14px; font-weight: 500; }}
    .amount {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; margin: 16px 0; }}
    .divider {{ border-top: 1px solid #e7e5e4; margin: 16px 0; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
    .badge-paid {{ background: #f0fdf4; color: #15803d; }}
    .badge-unpaid {{ background: #fffbeb; color: #b45309; }}
    .badge-unknown {{ background: #f5f5f4; color: #78716c; }}
    .desc {{ font-size: 13px; color: #57534e; line-height: 1.5; margin-top: 8px; }}
    .meta {{ font-size: 11px; color: #a8a29e; margin-top: 16px; }}
    .match {{ margin-top: 16px; padding: 12px; background: #f5f5f4; border-radius: 8px; }}
    .match-title {{ font-size: 11px; font-weight: 600; color: #78716c; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
    .match-item {{ font-size: 12px; color: #57534e; margin-bottom: 2px; }}
</style></head><body>
<div class="card">
    <h2>{vendor}</h2>
    <div class="subtitle">{subject}</div>
    <div class="amount">{amount_str} <span style="font-size:14px;font-weight:500;color:#a8a29e">{currency}</span></div>
    <div class="grid">
        <div class="field">
            <div class="field-label">Invoice Number</div>
            <div class="field-value">{inv_num}</div>
        </div>
        <div class="field">
            <div class="field-label">Payment Status</div>
            <div class="field-value"><span class="badge badge-{h(pay_status)}">{h(pay_status.title())}</span></div>
        </div>
        <div class="field">
            <div class="field-label">Invoice Date</div>
            <div class="field-value">{inv_date}</div>
        </div>
        <div class="field">
            <div class="field-label">Due Date</div>
            <div class="field-value">{due_date}</div>
        </div>
    </div>
    {'<div class="divider"></div><div class="field-label">Description</div><div class="desc">' + line_items + '</div>' if row.get('line_items') else ''}
    <div class="divider"></div>
    <div class="meta">
        From: {email_from}<br>
        Date: {email_date}<br>
        Confidence: {conf}%
    </div>
    {'<div class="match"><div class="match-title">Ramp Match (' + str(pay_conf) + '%)</div>' + ''.join(f'<div class="match-item">{h(str(d))}</div>' for d in details) + '</div>' if details else ''}
</div></body></html>"""
    return Response(content=html, media_type="text/html")

def _normalize_vendor(name):
    if not name:
        return ""
    import re
    n = name.lower().strip()
    n = re.sub(r'[,.\-_]', ' ', n)
    n = re.sub(r'\b(inc|ltd|llc|corp|co|gmbh|pty|oy|oü|sa|srl|bv|nv|ag)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def _vendor_matches(vendor_a, vendor_b):
    if not vendor_a or not vendor_b or len(vendor_a) < 3 or len(vendor_b) < 3:
        return False
    if vendor_a == vendor_b:
        return True
    shorter, longer = sorted([vendor_a, vendor_b], key=len)
    if len(shorter) < 4:
        return shorter == longer
    words_short = set(shorter.split())
    words_long = set(longer.split())
    if words_short and words_long and words_short.issubset(words_long):
        return True
    return shorter in longer or longer in shorter

def _normalize_invoice_number(num):
    if not num:
        return ""
    import re
    n = num.strip().lower()
    n = re.sub(r'^(inv|invoice|bill|receipt|ref|no|#)[.\-:\s#]*', '', n)
    n = re.sub(r'[\-\s]', '', n)
    n = n.lstrip('0') or '0'
    return n

def _get_ramp_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

async def _fetch_all_paginated(client, token, endpoint):
    headers = _get_ramp_headers(token)
    all_data = []
    url = f"{RAMP_BASE}/developer/v1/{endpoint}?page_size=100"
    while url:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            break
        data = resp.json()
        all_data.extend(data.get("data", []))
        url = data.get("page", {}).get("next")
    return all_data

async def _fetch_all_ramp_bills(client, token):
    return await _fetch_all_paginated(client, token, "bills")

async def _fetch_all_ramp_transactions(client, token):
    return await _fetch_all_paginated(client, token, "transactions")

async def _fetch_all_ramp_reimbursements(client, token):
    return await _fetch_all_paginated(client, token, "reimbursements")

def _get_bill_amount_cents(bill):
    amt = bill.get("amount")
    if isinstance(amt, dict):
        return amt.get("amount")
    return amt

def _get_bill_status(bill):
    return bill.get("status", "OPEN").upper()

def _get_bill_vendor_name(bill):
    vendor = bill.get("vendor")
    if isinstance(vendor, dict):
        return vendor.get("name", "")
    return ""

def _get_bill_vendor_id(bill):
    vendor = bill.get("vendor")
    if isinstance(vendor, dict):
        return vendor.get("id")
    return bill.get("vendor_id")

def _date_proximity_days(date1, date2):
    if not date1 or not date2:
        return None
    try:
        from datetime import datetime
        d1 = datetime.strptime(str(date1)[:10], "%Y-%m-%d")
        d2 = datetime.strptime(str(date2)[:10], "%Y-%m-%d")
        return abs((d1 - d2).days)
    except (ValueError, TypeError):
        return None

def _amount_matches(a, b):
    try:
        fa, fb = float(a), float(b)
        if fa == 0 and fb == 0:
            return True
        diff = abs(fa - fb)
        max_val = max(abs(fa), abs(fb))
        return diff <= max(0.50, max_val * 0.01)
    except (ValueError, TypeError):
        return False

def _score_invoice(invoice, ramp_bills, ramp_transactions, ramp_reimbursements):
    score = 0
    signals = []
    match_type = "needs_upload"
    ramp_bill_id = None
    ramp_vendor_id = None

    inv_num = _normalize_invoice_number(invoice.get("invoice_number") or "")
    inv_amount = invoice.get("amount")
    inv_currency = (invoice.get("currency") or "USD").upper()
    inv_vendor = _normalize_vendor(invoice.get("vendor_name"))
    inv_date = invoice.get("invoice_date")
    pdf_status = (invoice.get("payment_status") or "unknown").lower()

    # Signal 1: Match against Ramp bills
    best_bill = None
    best_bill_score = 0
    best_bill_reasons = []
    for bill in ramp_bills:
        bill_score = 0
        reasons = []
        bill_inv_num = _normalize_invoice_number(bill.get("invoice_number") or "")
        bill_vendor_name = _get_bill_vendor_name(bill)
        bill_vendor = _normalize_vendor(bill_vendor_name)
        bill_amount_raw = _get_bill_amount_cents(bill)
        bill_amount = float(bill_amount_raw) / 100 if bill_amount_raw else None
        bill_date = bill.get("issued_at") or bill.get("due_at")

        if inv_num and bill_inv_num and inv_num == bill_inv_num:
            bill_score += 40
            reasons.append(f"Invoice # match: {inv_num}")

        if inv_vendor and bill_vendor and _vendor_matches(inv_vendor, bill_vendor):
            bill_score += 15
            reasons.append(f"Vendor match: {bill_vendor_name}")

        bill_currency = (bill.get("currency") or "USD").upper()
        if isinstance(bill.get("amount"), dict):
            bill_currency = (bill["amount"].get("currency_code") or bill_currency).upper()
        if inv_amount and bill_amount and _amount_matches(inv_amount, bill_amount) and inv_currency == bill_currency:
            bill_score += 20
            reasons.append(f"Amount match: ${bill_amount:.2f}")

        days = _date_proximity_days(inv_date, bill_date)
        if days is not None and days <= 7:
            bill_score += 10
            reasons.append(f"Date within {days} days")
        elif days is not None and days <= 30:
            bill_score += 5
            reasons.append(f"Date within {days} days")

        if bill_score > best_bill_score:
            best_bill_score = bill_score
            best_bill = bill
            best_bill_reasons = reasons

    # Evaluate best bill match (but don't apply yet — compare with transactions first)
    has_identity_match = any("Invoice #" in r or "Vendor match" in r for r in best_bill_reasons)
    bill_qualified = best_bill and best_bill_score >= 35 and has_identity_match
    bill_effective_score = 0
    if bill_qualified:
        bill_status = _get_bill_status(best_bill)
        bill_effective_score = best_bill_score + (40 if bill_status == "PAID" else 15)

    # Signal 2: Match against Ramp card transactions
    best_txn = None
    best_txn_score = 0
    best_txn_reasons = []
    for txn in ramp_transactions:
        txn_score = 0
        reasons = []
        txn_merchant_name = txn.get("merchant_name") or txn.get("merchant_descriptor") or ""
        txn_merchant = _normalize_vendor(txn_merchant_name)
        txn_amount_raw = txn.get("amount")
        txn_amount = float(txn_amount_raw) if txn_amount_raw else None
        txn_date = (txn.get("user_transaction_time") or txn.get("synced_at") or "")[:10]

        if inv_vendor and txn_merchant and _vendor_matches(inv_vendor, txn_merchant):
            txn_score += 15
            reasons.append(f"Merchant match: {txn_merchant_name}")

        txn_currency = (txn.get("currency") or txn.get("original_currency_code") or "USD").upper()
        if inv_amount and txn_amount and _amount_matches(inv_amount, txn_amount) and inv_currency == txn_currency:
            txn_score += 20
            reasons.append(f"Amount match: ${txn_amount:.2f}")

        days = _date_proximity_days(inv_date, txn_date)
        if days is not None and days <= 7:
            txn_score += 10
            reasons.append(f"Date within {days} days")
        elif days is not None and days <= 30:
            txn_score += 5
            reasons.append(f"Date within {days} days")


        if txn_score > best_txn_score:
            best_txn_score = txn_score
            best_txn = txn
            best_txn_reasons = reasons

    ramp_transaction_id = None
    has_txn_vendor_match = any("Merchant match" in r for r in best_txn_reasons)
    txn_qualified = best_txn and best_txn_score >= 30 and has_txn_vendor_match
    txn_effective_score = best_txn_score + 35 if txn_qualified else 0

    # Pick whichever match is stronger — bill or transaction
    if bill_qualified and bill_effective_score >= txn_effective_score:
        bill_status = _get_bill_status(best_bill)
        bill_summary = (best_bill.get("status_summary") or "").upper()
        ramp_bill_id = best_bill.get("id")
        ramp_vendor_id = _get_bill_vendor_id(best_bill)
        bill_vendor_name = _get_bill_vendor_name(best_bill)
        score += bill_effective_score
        signals.append(f"Ramp bill {bill_status} — {bill_vendor_name} (ID: {ramp_bill_id})")
        signals.extend(best_bill_reasons)
        if bill_status == "PAID" or bill_summary == "PAYMENT_COMPLETED":
            match_type = "paid"
        elif bill_summary in ("DRAFT", "APPROVAL_PENDING") or bill_status == "DRAFT":
            match_type = "draft"
        else:
            match_type = "pending_payment"
    elif txn_qualified:
        score += txn_effective_score
        txn_id = best_txn.get("id")
        txn_merchant_name = best_txn.get("merchant_name") or best_txn.get("merchant_descriptor") or ""
        card_holder = best_txn.get("card_holder", {})
        holder_name = f"{card_holder.get('first_name', '')} {card_holder.get('last_name', '')}".strip() if isinstance(card_holder, dict) else ""
        signals.append(f"Ramp card transaction — {txn_merchant_name} by {holder_name} (ID: {txn_id})")
        signals.extend(best_txn_reasons)
        match_type = "paid"
        ramp_transaction_id = txn_id
    elif bill_qualified:
        bill_status = _get_bill_status(best_bill)
        bill_summary = (best_bill.get("status_summary") or "").upper()
        ramp_bill_id = best_bill.get("id")
        ramp_vendor_id = _get_bill_vendor_id(best_bill)
        bill_vendor_name = _get_bill_vendor_name(best_bill)
        score += bill_effective_score
        signals.append(f"Ramp bill {bill_status} — {bill_vendor_name} (ID: {ramp_bill_id})")
        signals.extend(best_bill_reasons)
        if bill_status == "PAID" or bill_summary == "PAYMENT_COMPLETED":
            match_type = "paid"
        elif bill_summary in ("DRAFT", "APPROVAL_PENDING") or bill_status == "DRAFT":
            match_type = "draft"
        else:
            match_type = "pending_payment"

    # Signal 3: Match against reimbursements (same rigor as bills/transactions)
    best_reimb = None
    best_reimb_score = 0
    best_reimb_reasons = []
    for reimb in ramp_reimbursements:
        reimb_score = 0
        reasons = []
        reimb_merchant_name = reimb.get("merchant") or ""
        reimb_merchant = _normalize_vendor(reimb_merchant_name)
        reimb_amount_raw = reimb.get("amount")
        reimb_amount = float(reimb_amount_raw) if reimb_amount_raw else None
        reimb_date = reimb.get("transaction_date") or (reimb.get("created_at") or "")[:10]
        reimb_user = reimb.get("user_full_name") or ""

        if inv_vendor and reimb_merchant and _vendor_matches(inv_vendor, reimb_merchant):
            reimb_score += 15
            reasons.append(f"Merchant match: {reimb_merchant_name}")

        reimb_currency = (reimb.get("currency") or "USD").upper()
        if inv_amount and reimb_amount and _amount_matches(inv_amount, reimb_amount) and inv_currency == reimb_currency:
            reimb_score += 20
            reasons.append(f"Amount match: ${reimb_amount:.2f}")

        days = _date_proximity_days(inv_date, reimb_date)
        if days is not None and days <= 7:
            reimb_score += 10
            reasons.append(f"Date within {days} days")
        elif days is not None and days <= 30:
            reimb_score += 5
            reasons.append(f"Date within {days} days")

        if reimb_score > best_reimb_score:
            best_reimb_score = reimb_score
            best_reimb = reimb
            best_reimb_reasons = reasons

    has_reimb_vendor_match = any("Merchant match" in r for r in best_reimb_reasons)
    if best_reimb and best_reimb_score >= 30 and has_reimb_vendor_match and match_type == "needs_upload":
        score += best_reimb_score + 25
        reimb_id = best_reimb.get("id")
        reimb_user = best_reimb.get("user_full_name") or ""
        reimb_merchant_name = best_reimb.get("merchant") or ""
        signals.append(f"Ramp reimbursement — {reimb_merchant_name} by {reimb_user} (ID: {reimb_id})")
        signals.extend(best_reimb_reasons)
        match_type = "paid"

    # Signal 4: PDF says paid
    if pdf_status == "paid":
        score += 30
        signals.append("PDF indicates paid")
        if match_type == "needs_upload":
            match_type = "paid"

    # Cap at 100
    score = min(score, 100)

    return {
        "payment_confidence": score,
        "match_type": match_type,
        "match_details": json.dumps(signals),
        "ramp_bill_id": ramp_bill_id,
        "ramp_vendor_id": ramp_vendor_id,
        "ramp_transaction_id": ramp_transaction_id,
        "ramp_status": match_type if match_type != "needs_upload" else "not_uploaded",
    }

def _match_ramp_bill(invoice, ramp_bills):
    inv_num = _normalize_invoice_number((invoice.get("invoice_number") or ""))
    inv_amount = invoice.get("amount")
    inv_vendor = _normalize_vendor(invoice.get("vendor_name"))

    for bill in ramp_bills:
        bill_inv_num = _normalize_invoice_number((bill.get("invoice_number") or ""))

        if inv_num and bill_inv_num and inv_num == bill_inv_num:
            return bill

        bill_vendor = _normalize_vendor(_get_bill_vendor_name(bill))
        if inv_vendor and bill_vendor and _vendor_matches(inv_vendor, bill_vendor):
            bill_amount_raw = _get_bill_amount_cents(bill)
            bill_amount = float(bill_amount_raw) / 100 if bill_amount_raw else None
            if inv_amount and bill_amount and _amount_matches(inv_amount, bill_amount):
                return bill

    return None

async def _find_ramp_vendor_id(client, token, vendor_name):
    headers = _get_ramp_headers(token)
    norm = _normalize_vendor(vendor_name)
    url = f"{RAMP_BASE}/developer/v1/vendors?page_size=100"
    while url:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            break
        data = resp.json()
        for v in data.get("data", []):
            if _vendor_matches(norm, _normalize_vendor(v.get("name", ""))):
                return v.get("id")
        url = data.get("page", {}).get("next")
    return None

@app.post("/api/invoices/{invoice_id}/upload-to-ramp")
async def upload_to_ramp(invoice_id: int):
    ramp_token = os.environ.get("RAMP_ACCESS_TOKEN")
    if not ramp_token:
        raise HTTPException(400, "Ramp not configured. Set RAMP_ACCESS_TOKEN in .env")

    conn = get_db()
    row = fetchone(conn, "SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    if not row:
        conn.close()
        raise HTTPException(404, "Invoice not found")

    invoice = dict(row)
    headers = _get_ramp_headers(ramp_token)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check if bill already exists in Ramp
        ramp_bills = await _fetch_all_ramp_bills(client, ramp_token)
        existing = _match_ramp_bill(invoice, ramp_bills)
        if existing:
            bill_id = existing.get("id")
            bill_status = _get_bill_status(existing)
            bill_summary = (existing.get("status_summary") or "").upper()
            if bill_status == "PAID" or bill_summary == "PAYMENT_COMPLETED":
                ramp_status = "paid"
            elif bill_summary in ("DRAFT", "APPROVAL_PENDING") or bill_status == "DRAFT":
                ramp_status = "draft"
            else:
                ramp_status = "pending_payment"
            execute(conn,
                "UPDATE invoices SET ramp_bill_id = %s, ramp_status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (bill_id, ramp_status, invoice_id))
            conn.commit()
            conn.close()
            return {"status": "already_exists", "ramp_bill_id": bill_id, "message": f"Already in Ramp — status: {ramp_status}"}

        # Find vendor_id: DB cache → vendor search
        vendor_id = invoice.get("ramp_vendor_id")
        if not vendor_id:
            norm = _normalize_vendor(invoice.get("vendor_name"))
            mapping = fetchone(conn, "SELECT ramp_vendor_id FROM vendor_mapping WHERE vendor_name_normalized = %s", (norm,))
            if mapping:
                vendor_id = mapping["ramp_vendor_id"]
        if not vendor_id and invoice.get("vendor_name"):
            vendor_id = await _find_ramp_vendor_id(client, ramp_token, invoice["vendor_name"])

        if not vendor_id:
            conn.close()
            raise HTTPException(400, f"Vendor '{invoice.get('vendor_name')}' not found in Ramp. Add them in Ramp first.")

        # Get entity_id
        entity_id = os.environ.get("RAMP_ENTITY_ID", "")
        if not entity_id:
            ent_resp = await client.get(f"{RAMP_BASE}/developer/v1/entities", headers=headers)
            if ent_resp.status_code == 200:
                entities = ent_resp.json().get("data", [])
                if entities:
                    entity_id = entities[0].get("id", "")

        # Build draft bill payload — only vendor_id required, rest optional
        draft_payload = {"vendor_id": vendor_id}
        if entity_id:
            draft_payload["entity_id"] = entity_id
        if invoice.get("invoice_number"):
            draft_payload["invoice_number"] = invoice["invoice_number"][:20]
        if invoice.get("invoice_date"):
            draft_payload["issued_at"] = invoice["invoice_date"]
        if invoice.get("due_date") or invoice.get("invoice_date"):
            draft_payload["due_at"] = invoice["due_date"] or invoice["invoice_date"]
        draft_payload["invoice_currency"] = invoice.get("currency") or "USD"
        if invoice.get("amount"):
            draft_payload["line_items"] = [{
                "amount": float(invoice["amount"]),
                "memo": invoice.get("line_items") or invoice.get("invoice_number") or "Invoice",
            }]

        resp = await client.post(f"{RAMP_BASE}/developer/v1/bills/drafts", headers=headers, json=draft_payload)
        if resp.status_code not in (200, 201):
            conn.close()
            raise HTTPException(resp.status_code, f"Ramp draft bill creation failed: {resp.text}")

        draft = resp.json()
        draft_id = draft.get("id")

        # Attach PDF if available
        if invoice.get("pdf_data") and draft_id:
            pdf_bytes = bytes(invoice["pdf_data"])
            filename = invoice.get("pdf_filename") or "invoice.pdf"
            att_headers = {"Authorization": f"Bearer {ramp_token}"}
            await client.post(
                f"{RAMP_BASE}/developer/v1/bills/drafts/{draft_id}/attachments",
                headers=att_headers,
                files={"file": (filename, pdf_bytes, "application/pdf")},
                data={"attachment_type": "INVOICE"})

        # Cache vendor mapping
        if invoice.get("vendor_name"):
            norm = _normalize_vendor(invoice["vendor_name"])
            execute(conn,
                """INSERT INTO vendor_mapping (vendor_name_normalized, ramp_vendor_id, ramp_vendor_name)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (vendor_name_normalized) DO UPDATE SET ramp_vendor_id = EXCLUDED.ramp_vendor_id""",
                (norm, vendor_id, invoice["vendor_name"]))

        execute(conn,
            "UPDATE invoices SET ramp_bill_id = %s, ramp_vendor_id = %s, ramp_status = 'draft', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (draft_id, vendor_id, invoice_id))
        conn.commit()
        conn.close()

    return {"status": "draft", "ramp_bill_id": draft_id, "message": "Draft bill created in Ramp"}

@app.post("/api/sync-ramp-status")
async def sync_ramp_status():
    ramp_token = os.environ.get("RAMP_ACCESS_TOKEN")
    if not ramp_token:
        raise HTTPException(400, "Ramp not configured")

    conn = get_db()
    scored = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        ramp_bills, ramp_transactions, ramp_reimbursements = await asyncio.gather(
            _fetch_all_ramp_bills(client, ramp_token),
            _fetch_all_ramp_transactions(client, ramp_token),
            _fetch_all_ramp_reimbursements(client, ramp_token),
        )

        invoices_to_score = fetchall(conn,
            """SELECT id, vendor_name, amount, currency, invoice_number, invoice_date,
                      due_date, payment_status, ramp_bill_id
               FROM invoices WHERE is_invoice = TRUE AND confidence >= 50""")

        for row in invoices_to_score:
            inv = dict(row)
            result = _score_invoice(inv, ramp_bills, ramp_transactions, ramp_reimbursements)

            execute(conn,
                """UPDATE invoices SET
                    payment_confidence = %s, match_type = %s, match_details = %s,
                    ramp_bill_id = %s,
                    ramp_vendor_id = %s,
                    ramp_transaction_id = %s,
                    ramp_status = %s,
                    updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s""",
                (result["payment_confidence"], result["match_type"], result["match_details"],
                 result["ramp_bill_id"], result["ramp_vendor_id"], result["ramp_transaction_id"],
                 result["ramp_status"], row["id"]))

            if result["ramp_vendor_id"] and inv.get("vendor_name"):
                norm = _normalize_vendor(inv["vendor_name"])
                execute(conn,
                    """INSERT INTO vendor_mapping (vendor_name_normalized, ramp_vendor_id, ramp_vendor_name)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (vendor_name_normalized) DO UPDATE SET ramp_vendor_id = EXCLUDED.ramp_vendor_id""",
                    (norm, result["ramp_vendor_id"], inv["vendor_name"]))
            scored += 1

    conn.commit()
    conn.close()
    return {
        "scored": scored,
        "ramp_bills": len(ramp_bills),
        "ramp_transactions": len(ramp_transactions),
        "ramp_reimbursements": len(ramp_reimbursements),
    }

class OverridePayload(BaseModel):
    is_invoice: Optional[bool] = None
    confidence: Optional[int] = None
    dismissed: Optional[bool] = None

@app.patch("/api/invoices/{invoice_id}")
def update_invoice(invoice_id: int, payload: OverridePayload):
    conn = get_db()
    row = fetchone(conn, "SELECT id FROM invoices WHERE id = %s", (invoice_id,))
    if not row:
        conn.close()
        raise HTTPException(404, "Invoice not found")
    updates = []
    params = []
    if payload.dismissed is not None:
        updates.append("is_invoice = %s")
        params.append(not payload.dismissed)
        if payload.dismissed:
            updates.append("confidence = %s")
            params.append(0)
    elif payload.is_invoice is not None:
        updates.append("is_invoice = %s")
        params.append(payload.is_invoice)
    if payload.confidence is not None:
        updates.append("confidence = %s")
        params.append(payload.confidence)
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(invoice_id)
        execute(conn, f"UPDATE invoices SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/invoices/export")
def export_csv_route():
    conn = get_db()
    rows = fetchall(conn,
        """SELECT vendor_name, amount, currency, invoice_number, invoice_date, due_date,
           line_items, email_subject, email_from, ramp_status, confidence,
           payment_status, payment_confidence, match_type, match_details, source_type
           FROM invoices WHERE is_invoice = TRUE AND confidence >= 50
           ORDER BY invoice_date DESC""")
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Vendor", "Amount", "Currency", "Invoice #", "Invoice Date", "Due Date",
                     "Description", "Email Subject", "From", "Ramp Status", "Confidence",
                     "Payment Status", "Match Score", "Match Type", "Match Details", "Source"])
    for r in rows:
        writer.writerow([r["vendor_name"], r["amount"], r["currency"], r["invoice_number"],
                        r["invoice_date"], r["due_date"], r["line_items"], r["email_subject"],
                        r["email_from"], r["ramp_status"], r["confidence"],
                        r["payment_status"], r["payment_confidence"], r["match_type"],
                        r["match_details"], r["source_type"]])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices.csv"})

@app.get("/api/vendors/summary")
def vendor_summary():
    conn = get_db()
    rows = fetchall(conn,
        """SELECT vendor_name,
           COUNT(*) as invoice_count,
           SUM(amount) as total_amount,
           MIN(invoice_date) as earliest_date,
           MAX(invoice_date) as latest_date,
           SUM(CASE WHEN ramp_status = 'not_uploaded' THEN 1 ELSE 0 END) as pending_count,
           SUM(CASE WHEN ramp_status != 'not_uploaded' THEN 1 ELSE 0 END) as uploaded_count
           FROM invoices
           WHERE is_invoice = TRUE AND confidence >= 50 AND vendor_name IS NOT NULL
           GROUP BY vendor_name
           ORDER BY total_amount DESC""")
    conn.close()
    return rows

@app.post("/api/scan-gmail")
def scan_gmail():
    from gmail_scraper import fetch_new_invoices
    count = fetch_new_invoices()
    return {"new_invoices": count}

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "frontend"), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
