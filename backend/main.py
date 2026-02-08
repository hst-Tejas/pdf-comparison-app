from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
import fitz
import hashlib
import re
import difflib
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
REPORT_PATH = "comparison_report.pdf"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------- Strict Comparison -----------

def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_visual_hash(page, dpi=144):
    pix = page.get_pixmap(dpi=dpi)
    return hashlib.sha256(pix.samples).hexdigest()
    
def extract_text_blocks(page):
    """
    Returns list of text blocks with bounding boxes.
    """
    blocks = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_ = b
        clean = normalize_text(text)
        if clean:
            blocks.append({
                "text": clean,
                "x": x0,
                "y": y0,
                "width": x1 - x0,
                "height": y1 - y0
            })
    return blocks
    


def analyze_pdf(path):
    doc = fitz.open(path)
    pages = []
    for page in doc:
        pages.append({
            "text": normalize_text(page.get_text("text")),
            "visual_hash": get_visual_hash(page)
        })
    doc.close()
    return pages


@app.post("/compare")
async def compare_pdfs(
    before: UploadFile = File(...),
    after: UploadFile = File(...)
):
    before_path = os.path.join(UPLOAD_DIR, "before.pdf")
    after_path = os.path.join(UPLOAD_DIR, "after.pdf")

    with open(before_path, "wb") as f:
        shutil.copyfileobj(before.file, f)

    with open(after_path, "wb") as f:
        shutil.copyfileobj(after.file, f)

    before_pages = analyze_pdf(before_path)
    after_pages = analyze_pdf(after_path)

    differences = []
    text_differences = {}

    before_doc = fitz.open(before_path)
    after_doc = fitz.open(after_path)

    for i in range(min(len(before_doc), len(after_doc))):
        issues = []
        page_diffs = []

        before_blocks = extract_text_blocks(before_doc[i])
        after_blocks = extract_text_blocks(after_doc[i])

        before_texts = [b["text"] for b in before_blocks]
        after_texts = [b["text"] for b in after_blocks]

        diff = difflib.SequenceMatcher(None, before_texts, after_texts)

        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            if tag in ("replace", "insert", "delete"):
                issues.append("TEXT")
                for b in after_blocks[j1:j2]:
                    page_diffs.append({
                        "x": b["x"],
                        "y": b["y"],
                        "width": b["width"],
                        "height": b["height"]
                    })

        if before_pages[i]["visual_hash"] != after_pages[i]["visual_hash"]:
            issues.append("VISUAL")

        if issues:
            differences.append({
                "page": i + 1,
                "issues": list(set(issues))
            })

            if page_diffs:
                text_differences[str(i + 1)] = page_diffs

    before_doc.close()
    after_doc.close()

    generate_report(differences)

    return {
        "match": len(differences) == 0,
        "differences": differences,
        "changed_pages": [d["page"] for d in differences],
        "total_pages": len(before_pages),
        "text_differences": text_differences,
        "before_url": "/preview/before",
        "after_url": "/preview/after",
        "report_url": "/download-report"
    }







# ----------- PDF Preview -----------

@app.get("/preview/{type}")
def preview_pdf(type: str):
    path = os.path.join(UPLOAD_DIR, f"{type}.pdf")
    return FileResponse(path, media_type="application/pdf")


# ----------- Generate Downloadable Report -----------

def generate_report(differences):
    doc = SimpleDocTemplate(REPORT_PATH)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("PDF Comparison Report", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    data = [["Page", "Issues"]]
    for diff in differences:
        data.append([str(diff["page"]), ", ".join(diff["issues"])])

    if len(data) == 1:
        data.append(["All Pages", "MATCH"])

    table = Table(data)
    elements.append(table)

    doc.build(elements)


@app.get("/download-report")
def download_report():
    return FileResponse(REPORT_PATH, media_type="application/pdf", filename="comparison_report.pdf")
