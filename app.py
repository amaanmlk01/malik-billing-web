from flask import (
    Flask,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    redirect,
    url_for,
    jsonify,
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime, timedelta
import os
import sqlite3
import qrcode


app = Flask(__name__)
app.secret_key = "malik_secret_123"

# -----------------------------
# PATHS / CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BUSINESS_NAME = "MASOOM FOOT STYLE"
PARENT_COMPANY_NAME = "Bharti Airtel Limited"

BUSINESS_ADDRESS = "Achabal, Sopore, Jammu and Kashmir, Baramulla, 193201"
BUSINESS_MOBILE = "9906655252"
BUSINESS_GSTIN = "01BKLPM2422A1ZY"
BUSINESS_EMAIL = "emonmalik224@gmail.com"

BANK_ACCOUNT_NAME = "Masoom foot style"
BANK_IFSC = "JAKA0ACHBAL"
BANK_ACCOUNT_NO = "0221010100000480"
BANK_NAME = "Jammu and Kashmir Bank, ACHABAL SOPORE"
UPI_ID = "emonmalik224-5@oksbi"

INVOICE_FOLDER = os.path.join(BASE_DIR, "invoices")
INVOICE_COUNTER_FILE = os.path.join(BASE_DIR, "invoice_counter.txt")
DB_FILE = os.path.join(BASE_DIR, "billing.db")

LOGO_IMAGE_PATH = os.path.join(BASE_DIR, "static", "images", "logo.png")
SIGNATURE_IMAGE_PATH = os.path.join(BASE_DIR, "static", "images", "signature.png")

CRIMSON = colors.HexColor("#D32F2F")
DARK_GREY = colors.HexColor("#424242")
MID_GREY = colors.HexColor("#9E9E9E")
LIGHT_GREY = colors.HexColor("#F1F1F1")
LINE_GREY = colors.HexColor("#D0D0D0")


# -----------------------------
# HELPERS
# -----------------------------
def safe_float(value, default=0.0):
    try:
        s = str(value).strip()
        if s == "":
            return default
        return float(s.replace(",", ""))
    except Exception:
        return default


def format_money(value):
    val = safe_float(value)
    if float(val).is_integer():
        return f"₹ {val:,.0f}"
    return f"₹ {val:,.2f}"


def number_to_words(n):
    units = [
        "",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
    ]

    tens = [
        "",
        "",
        "Twenty",
        "Thirty",
        "Forty",
        "Fifty",
        "Sixty",
        "Seventy",
        "Eighty",
        "Ninety",
    ]

    def convert_nn(num):
        if num < 20:
            return units[num]
        return tens[num // 10] + (" " + units[num % 10] if num % 10 else "")

    def convert_nnn(num):
        word = ""
        if num >= 100:
            word += units[num // 100] + " Hundred "
            num %= 100
        if num:
            word += convert_nn(num)
        return word.strip()

    if n == 0:
        return "Zero"

    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    hundred = n

    result = ""
    if crore:
        result += convert_nnn(crore) + " Crore "
    if lakh:
        result += convert_nnn(lakh) + " Lakh "
    if thousand:
        result += convert_nnn(thousand) + " Thousand "
    if hundred:
        result += convert_nnn(hundred)

    return result.strip()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no INTEGER,
            invoice_date TEXT,
            due_date TEXT,
            bill_to TEXT,
            ship_to TEXT,
            gstin TEXT,
            subtotal TEXT,
            received TEXT,
            balance TEXT,
            pdf_file TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_to TEXT UNIQUE,
            ship_to TEXT,
            gstin TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def get_next_invoice_number():
    if not os.path.exists(INVOICE_COUNTER_FILE):
        with open(INVOICE_COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write("1000")

    with open(INVOICE_COUNTER_FILE, "r", encoding="utf-8") as f:
        current = int(f.read().strip())

    current += 1

    with open(INVOICE_COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(current))

    return current


def generate_upi_qr_image(upi_id, amount=None, note="Invoice Payment"):
    payload = f"upi://pay?pa={upi_id}&pn={BANK_ACCOUNT_NAME}"
    amt = safe_float(amount)
    if amt > 0:
        payload += f"&am={amt:.2f}"
    if note:
        payload += f"&tn={note.replace(' ', '%20')}"

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return ImageReader(img)


# -----------------------------
# AUTH ROUTES
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "1234":
            session["user"] = username
            return redirect(url_for("home"))

        return """
        <html>
        <body style="font-family:Arial;background:#0b1220;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
            <div style="background:#111827;padding:30px;border-radius:12px;width:320px;">
                <h2 style="margin-top:0;">Malik Billing Login</h2>
                <p style="color:#ff6b6b;">Invalid Credentials</p>
                <a href="/login" style="color:#60a5fa;">Try Again</a>
            </div>
        </body>
        </html>
        """

    return """
    <html>
    <head>
        <title>Login - Malik Billing</title>
    </head>
    <body style="font-family:Arial;background:#0b1220;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
        <div style="background:#111827;padding:30px;border-radius:12px;width:320px;">
            <h2 style="margin-top:0;">Malik Billing Login</h2>
            <form method="POST">
                <input name="username" placeholder="Username" style="width:100%;padding:10px;margin-bottom:12px;border:none;border-radius:8px;box-sizing:border-box;">
                <input name="password" type="password" placeholder="Password" style="width:100%;padding:10px;margin-bottom:12px;border:none;border-radius:8px;box-sizing:border-box;">
                <button type="submit" style="width:100%;padding:10px;background:#2563eb;color:white;border:none;border-radius:8px;">Login</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# -----------------------------
# APP ROUTES
# -----------------------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT invoice_no, invoice_date, bill_to, subtotal, received, balance, pdf_file
        FROM invoices
        ORDER BY id DESC
        """
    )

    invoices = cursor.fetchall()
    conn.close()

    return render_template("history.html", invoices=invoices)


@app.route("/invoice/<filename>")
def open_invoice_file(filename):
    if "user" not in session:
        return redirect(url_for("login"))
    return send_from_directory(INVOICE_FOLDER, filename, as_attachment=False)


@app.route("/customers")
def get_customers():
    if "user" not in session:
        return jsonify({"customers": []})

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT bill_to, ship_to, gstin FROM customers ORDER BY bill_to ASC")
    rows = cursor.fetchall()
    conn.close()

    customers = []
    for row in rows:
        customers.append(
            {
                "bill_to": row[0],
                "ship_to": row[1],
                "gstin": row[2],
            }
        )

    return jsonify({"customers": customers})


@app.route("/generate", methods=["POST"])
def generate_invoice():
    if "user" not in session:
        return redirect(url_for("login"))

    data = request.json or {}

    bill_to = data.get("billTo", "") or ""
    ship_to = data.get("shipTo", "") or ""
    gstin = data.get("gstin", "") or ""
    items = data.get("items", []) or []
    subtotal = data.get("subtotal", "0") or "0"
    received = data.get("received", "0") or "0"
    balance = data.get("balance", "0") or "0"

    if not os.path.exists(INVOICE_FOLDER):
        os.makedirs(INVOICE_FOLDER)

    invoice_no = get_next_invoice_number()
    invoice_date = datetime.now()
    due_date = invoice_date + timedelta(days=7)

    filename = f"invoice_{invoice_no}.pdf"
    filepath = os.path.join(INVOICE_FOLDER, filename)

    # -----------------------------
    # PDF LAYOUT
    # -----------------------------
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    ml = 32
    mr = 32
    top = height - 28
    usable_w = width - ml - mr

    # Header
    y = top

    # Left label
    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(ml, y, "BILL OF SUPPLY")

    box_x = ml + 82
    box_y = y - 7
    box_w = 52
    box_h = 14
    c.setStrokeColor(MID_GREY)
    c.rect(box_x, box_y, box_w, box_h, stroke=1, fill=0)
    c.setFillColor(MID_GREY)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(box_x + box_w / 2, box_y + 4, "ORIGINAL")

    # Right company
    c.setFillColor(MID_GREY)
    c.setFont("Helvetica", 9)
    c.drawRightString(width - mr, y, PARENT_COMPANY_NAME)

    header_y = y - 28

    # Logo
    if os.path.exists(LOGO_IMAGE_PATH):
        try:
            logo = ImageReader(LOGO_IMAGE_PATH)
            c.drawImage(
                logo,
                ml,
                header_y - 48,
                width=72,
                height=72,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # Center branding
    center_x = width / 2
    c.setFillColor(CRIMSON)
    c.setFont("Times-Bold", 20)
    c.drawCentredString(center_x, header_y, BUSINESS_NAME)

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica", 9)
    c.drawCentredString(center_x, header_y - 17, BUSINESS_ADDRESS)
    c.drawCentredString(
        center_x,
        header_y - 31,
        f"Mobile:  {BUSINESS_MOBILE}     GSTIN:  {BUSINESS_GSTIN}",
    )
    c.drawCentredString(center_x, header_y - 45, f"Email:  {BUSINESS_EMAIL}")

    # Thick red divider
    divider_y = header_y - 64
    c.setFillColor(CRIMSON)
    c.rect(ml, divider_y, usable_w, 5, fill=1, stroke=0)

    # Metadata bar
    meta_y = divider_y - 30
    meta_h = 28
    c.setFillColor(LIGHT_GREY)
    c.rect(ml, meta_y, usable_w, meta_h, fill=1, stroke=0)

    col1 = ml + 12
    col2 = ml + usable_w / 3 + 12
    col3 = ml + 2 * usable_w / 3 + 12

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(col1, meta_y + 17, "Invoice No.:")
    c.drawString(col2, meta_y + 17, "Invoice Date:")
    c.drawString(col3, meta_y + 17, "Due Date:")

    c.setFont("Helvetica", 9)
    c.drawString(col1 + 55, meta_y + 17, str(invoice_no))
    c.drawString(col2 + 62, meta_y + 17, invoice_date.strftime("%d/%m/%Y"))
    c.drawString(col3 + 48, meta_y + 17, due_date.strftime("%d/%m/%Y"))

    # Address section
    addr_top = meta_y - 22
    left_col_x = ml
    right_col_x = width / 2 + 10

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_col_x, addr_top, "BILL TO")
    c.drawString(right_col_x, addr_top, "SHIP TO")

    c.setFont("Helvetica-Bold", 10)
    if bill_to:
        c.drawString(left_col_x, addr_top - 18, bill_to.split(",")[0][:46])
    if ship_to:
        c.drawString(right_col_x, addr_top - 18, ship_to.split(",")[0][:40])

    c.setFont("Helvetica", 9)

    bill_lines = [x.strip() for x in bill_to.split(",") if x.strip()]
    ship_lines = [x.strip() for x in ship_to.split(",") if x.strip()]

    bill_y = addr_top - 34
    for line in bill_lines[1:6]:
        c.drawString(left_col_x, bill_y, line[:62])
        bill_y -= 12

    ship_y = addr_top - 34
    for line in ship_lines[1:5]:
        c.drawString(right_col_x, ship_y, line[:42])
        ship_y -= 12

    c.setFont("Helvetica", 9)
    c.drawString(left_col_x, min(bill_y, ship_y) - 6, f"GSTIN:  {gstin if gstin else '-'}")

    # Itemized table
    table_top = min(bill_y, ship_y) - 34
    table_left = ml
    table_right = width - mr

    c.setStrokeColor(CRIMSON)
    c.setLineWidth(1)
    c.line(table_left, table_top, table_right, table_top)

    header_line_y = table_top - 18
    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 10)

    item_x = table_left + 8
    qty_x = table_left + 330
    rate_x = table_left + 420
    amount_x = table_right - 8

    c.drawString(item_x, header_line_y, "ITEMS")
    c.drawCentredString(qty_x, header_line_y, "QTY.")
    c.drawCentredString(rate_x, header_line_y, "RATE")
    c.drawRightString(amount_x, header_line_y, "AMOUNT")

    line_under_header_y = header_line_y - 8
    c.setStrokeColor(CRIMSON)
    c.line(table_left, line_under_header_y, table_right, line_under_header_y)

    body_start_y = line_under_header_y - 18
    row_h = 26
    min_rows = 5
    render_rows = max(min_rows, len(items))

    c.setStrokeColor(LINE_GREY)
    c.setFont("Helvetica", 9)

    y_row = body_start_y
    for idx in range(render_rows):
        if idx < len(items):
            item = items[idx]
            name = str(item.get("name", ""))
            qty = str(item.get("qty", ""))
            rate = str(item.get("rate", ""))
            amount = str(item.get("amount", ""))

            c.setFillColor(DARK_GREY)
            c.drawString(item_x, y_row, name[:46])
            c.drawCentredString(qty_x, y_row, qty)
            c.drawCentredString(rate_x, y_row, rate)
            c.drawRightString(amount_x, y_row, amount)

        c.line(table_left, y_row - 10, table_right, y_row - 10)
        y_row -= row_h

    # Subtotal band
    subtotal_y = y_row - 2
    c.setStrokeColor(CRIMSON)
    c.line(table_left, subtotal_y + 10, table_right, subtotal_y + 10)

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left + 8, subtotal_y, "SUBTOTAL")
    c.drawCentredString(qty_x, subtotal_y, "1" if len(items) > 0 else "")
    c.drawRightString(amount_x, subtotal_y, format_money(subtotal))

    c.setStrokeColor(CRIMSON)
    c.line(table_left, subtotal_y - 8, table_right, subtotal_y - 8)

    # Lower section
    lower_top = subtotal_y - 30
    lower_bottom_target = 88

    # Left block
    left_block_x = table_left
    current_y = lower_top

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_block_x, current_y, "BANK DETAILS")
    current_y -= 14

    c.setFont("Helvetica", 9)
    c.drawString(left_block_x, current_y, "Name:")
    c.drawString(left_block_x + 82, current_y, BANK_ACCOUNT_NAME)
    current_y -= 14

    c.drawString(left_block_x, current_y, "IFSC Code:")
    c.drawString(left_block_x + 82, current_y, BANK_IFSC)
    current_y -= 14

    c.drawString(left_block_x, current_y, "Account No:")
    c.drawString(left_block_x + 82, current_y, BANK_ACCOUNT_NO)
    current_y -= 14

    c.drawString(left_block_x, current_y, "Bank:")
    c.drawString(left_block_x + 82, current_y, "Jammu and Kashmir Bank, ACHABAL")
    current_y -= 12
    c.drawString(left_block_x + 82, current_y, "SOPORE")

    qr_title_y = current_y - 24
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_block_x, qr_title_y, "PAYMENT QR CODE")

    qr_box_y = qr_title_y - 76
    qr_left = left_block_x + 135

    c.setFont("Helvetica", 9)
    c.drawString(left_block_x, qr_title_y - 18, "UPI ID:")
    c.drawString(left_block_x, qr_title_y - 32, UPI_ID)

    try:
        qr_reader = generate_upi_qr_image(
            UPI_ID,
            amount=safe_float(subtotal),
            note=f"Invoice {invoice_no}",
        )
        c.drawImage(
            qr_reader,
            qr_left,
            qr_box_y,
            width=66,
            height=66,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        c.rect(qr_left, qr_box_y, 66, 66, stroke=1, fill=0)

    terms_y = qr_box_y - 28
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_block_x, terms_y, "TERMS AND CONDITIONS")
    c.setFont("Helvetica", 9)
    c.drawString(left_block_x, terms_y - 16, "1. Goods once sold will not be taken back or exchanged")
    c.drawString(left_block_x, terms_y - 29, "2. All disputes are subject to local jurisdiction only")

    # Right totals
    totals_x = width - mr - 220
    totals_right = width - mr
    totals_top = lower_top + 2

    c.setStrokeColor(LINE_GREY)
    c.line(totals_x, totals_top, totals_right, totals_top)

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica", 10)
    c.drawString(totals_x + 6, totals_top - 15, "Total Amount")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(totals_right - 6, totals_top - 15, format_money(subtotal))

    c.setStrokeColor(LINE_GREY)
    c.line(totals_x, totals_top - 23, totals_right, totals_top - 23)

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica", 10)
    c.drawString(totals_x + 6, totals_top - 40, "Received Amount")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(totals_right - 6, totals_top - 40, format_money(received))

    total_box_y = totals_top - 78
    total_box_h = 28
    c.setFillColor(LIGHT_GREY)
    c.rect(totals_x, total_box_y, totals_right - totals_x, total_box_h, fill=1, stroke=0)

    c.setFillColor(DARK_GREY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(totals_x + 6, total_box_y + 9, "Balance Due")
    c.drawRightString(totals_right - 6, total_box_y + 9, format_money(balance))

    words_y = total_box_y - 30
    balance_value = safe_float(balance, 0.0)
    balance_int = int(balance_value)
    amount_words = number_to_words(balance_int) + " Rupees"

    c.setFont("Helvetica-Bold", 10)
    c.drawString(totals_x, words_y, "Total Amount (in words)")
    c.setFont("Helvetica", 9)

    line_y = words_y - 14
    words = amount_words.split()
    line = ""
    max_chars = 30
    for word in words:
        test = (line + " " + word).strip()
        if len(test) <= max_chars:
            line = test
        else:
            c.drawString(totals_x, line_y, line)
            line_y -= 11
            line = word
    if line:
        c.drawString(totals_x, line_y, line)

    # Signature
    sig_y = lower_bottom_target + 18
    if os.path.exists(SIGNATURE_IMAGE_PATH):
        try:
            sign = ImageReader(SIGNATURE_IMAGE_PATH)
            c.drawImage(
                sign,
                totals_right - 110,
                sig_y,
                width=84,
                height=40,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 9.5)
    c.drawRightString(totals_right, sig_y - 12, "AUTHORISED SIGNATORY FOR")
    c.drawRightString(totals_right, sig_y - 26, BUSINESS_NAME)

    c.save()

    # Save database record
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO invoices (
            invoice_no,
            invoice_date,
            due_date,
            bill_to,
            ship_to,
            gstin,
            subtotal,
            received,
            balance,
            pdf_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_no,
            invoice_date.strftime("%d-%m-%Y"),
            due_date.strftime("%d-%m-%Y"),
            bill_to,
            ship_to,
            gstin,
            subtotal,
            received,
            balance,
            filename,
        ),
    )

    cursor.execute("SELECT id FROM customers WHERE bill_to = ?", (bill_to,))
    existing_customer = cursor.fetchone()

    if existing_customer:
        cursor.execute(
            """
            UPDATE customers
            SET ship_to = ?, gstin = ?
            WHERE bill_to = ?
            """,
            (ship_to, gstin, bill_to),
        )
    else:
        cursor.execute(
            """
            INSERT INTO customers (bill_to, ship_to, gstin)
            VALUES (?, ?, ?)
            """,
            (bill_to, ship_to, gstin),
        )

    conn.commit()
    conn.close()

    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)