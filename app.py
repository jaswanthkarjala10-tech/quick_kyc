import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import re
import pytesseract
from PIL import Image
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
CORS(app)

os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# --- RISK ENGINE ---
def calculate_risk(extracted_text, user_name):
    score = 0
    reasons = []
    text = extracted_text.upper()
    user_name = user_name.upper()

    # Rule 1: PAN Format
    pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
    pan_match = re.search(pan_pattern, text)
    if not pan_match:
        score += 40
        reasons.append("PAN format invalid or not found - Possible fake document")
    
    # Rule 2: Name Mismatch
    if user_name not in text and len(user_name) > 2:
        score += 40
        reasons.append(f"Name mismatch: Form says '{user_name}' but document has different name")
    
    # Rule 3: High Cash Keyword
    if "CASH" in text or "1,00,000" in text or "100000" in text:
        score += 30
        reasons.append("High cash transaction keyword detected")

    # Rule 4: Multiple Cities
    cities = ["MUMBAI", "DELHI", "CHENNAI", "KOLKATA", "BANGALORE"]
    found_cities = [c for c in cities if c in text]
    if len(found_cities) >= 2:
        score += 20
        reasons.append(f"Multiple locations in short time: {', '.join(found_cities)}")

    if score == 0:
        reasons.append("Document verified - No risk indicators found")
    
    score = min(score, 100)
    status = "LOW"
    if score >= 70: status = "HIGH"
    elif score >= 40: status = "MEDIUM"
    
    return score, reasons, status, pan_match.group(0) if pan_match else "NOT FOUND"

# --- PDF GENERATOR ---
def generate_sar_report(name, pan, score, reasons):
    filename = f"reports/SAR_{pan}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(filename)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "BNP Paribas - Suspicious Activity Report (SAR)")
    c.setFont("Helvetica", 12)
    c.drawString(100, 770, f"Date: {datetime.now()}")
    c.drawString(100, 750, f"Customer: {name}")
    c.drawString(100, 730, f"PAN: {pan}")
    c.drawString(100, 710, f"Risk Score: {score}/100 - HIGH RISK")
    c.drawString(100, 680, "Reasons for Flagging:")
    y = 660
    for r in reasons:
        c.drawString(120, y, f"- {r}")
        y -= 20
    c.save()
    return filename

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload():
    try:
        name = request.form.get("customer_name", "").strip()
        file = request.files.get("pan_file")

        if not name or not file:
            return jsonify({"error": "Name and file required"}), 400

        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)

        # OCR
        try:
            img = Image.open(filepath)
            extracted_text = pytesseract.image_to_string(img)
        except Exception as e:
            extracted_text = f"OCR Error {str(e)}"

        # Risk Calculation
        score, reasons, status, pan = calculate_risk(extracted_text, name)

        # Generate SAR if high risk
        report_path = None
        if status == "HIGH":
            report_path = generate_sar_report(name, pan, score, reasons)

        # Render Result Page
        return render_template("result.html", 
                               name=name, pan=pan, score=score, 
                               status=status, reasons=reasons, 
                               text=extracted_text, report=report_path)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/risk", methods=["POST"])
def api_risk():
    data = request.get_json()
    text = data.get("document_text", "")
    name = data.get("name", "")
    score, reasons, status, pan = calculate_risk(text, name)
    return jsonify({"pan": pan, "score": score, "status": status, "reasons": reasons})

if __name__ == "__main__":
    app.run(debug=True)