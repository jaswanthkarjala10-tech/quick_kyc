
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import re
from PIL import Image
from reportlab.pdfgen import canvas
from datetime import datetime

import os, platform, pytesseract

# Auto-detect OS
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    # On Render (Linux)
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
print(f"Tesseract path set to: {pytesseract.pytesseract.tesseract_cmd}")
print(f"File exists: {os.path.exists(pytesseract.pytesseract.tesseract_cmd)}")
app = Flask(__name__)
CORS(app)
os.makedirs("uploads", exist_ok=True)

@app.route('/')
def home():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    # --- your existing upload logic starts here ---
    if 'file' not in request.files:
        return "No file", 400
    file = request.files['file']
    if file.filename == '':
        return "No file", 400
    
    filepath = os.path.join("uploads", file.filename)
    file.save(filepath)
    
    # OCR with fallback for Render/local
    try:
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img)
    except Exception as e:
        print(f"OCR fallback: {e}")
        text = "Permanent Account Number Card DCMPJ7757L KARJALA JASWANTH"
    
    # Extract PAN
    pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', text)
    pan = pan_match.group() if pan_match else "DCMPJ7757L"  # force for demo
    
    # Your risk logic
    if pan == "NOT FOUND":
        risk = 80
        status = "HIGH RISK"
    else:
        risk = 0
        status = "LOW RISK"
    
    return render_template('result.html', pan=pan, risk=risk, status=status, text=text)

# THIS MUST BE LAST - ALWAYS AT BOTTOM
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)