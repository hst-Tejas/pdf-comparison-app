📄 PDF Comparison Tool

A web-based enterprise PDF comparison system that detects text and visual differences, highlights changes, and generates a downloadable validation report.

🚀 Features

Side-by-side PDF preview

Text block-level comparison

Visual layout hash comparison

Yellow highlight for changed content

PASS / FAIL validation badge

Confidence score (%)

Page-level summary panel

Downloadable comparison report

🏗 Tech Stack

Backend

FastAPI

PyMuPDF (fitz)

difflib

ReportLab

Frontend

HTML / CSS / JavaScript

PDF.js (CDN)

📂 Project Structure
pdf-comparison-app/
├── backend/
│   ├── main.py
│   └── temp_uploads/
├── frontend/
│   └── index.html
└── README.md

⚙️ Setup
1️⃣ Install Dependencies

Inside backend/:

pip install fastapi uvicorn pymupdf reportlab python-multipart

2️⃣ Start Backend
uvicorn main:app --reload


Runs at:

http://127.0.0.1:8000

3️⃣ Start Frontend

Inside frontend/:

python -m http.server 5500 --bind 127.0.0.1


Open in browser:

http://127.0.0.1:5500/index.html

🔍 How It Works

Upload BEFORE and AFTER PDFs

Backend extracts text blocks + visual hashes

Differences are computed per page

Changed text blocks are returned with coordinates

Frontend highlights changes and displays summary

📊 Confidence Formula
Confidence = (Matching Pages / Total Pages) × 100

📄 API Endpoint
POST /compare

Form-data:

before (PDF)

after (PDF)

Returns:

{
  "changed_pages": [1],
  "total_pages": 5,
  "text_differences": { ... },
  "report_url": "/download-report"
}

📥 Report Download
GET /download-report


Generates a PDF summary report of detected differences.

🎯 Use Cases

Document migration validation

Compliance verification

Legal document comparison

Version auditing
