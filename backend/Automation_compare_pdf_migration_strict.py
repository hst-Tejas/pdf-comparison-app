#!/usr/bin/env python3

import sys
import re
import hashlib
from pathlib import Path

import fitz  # PyMuPDF


# ---------- Helpers ----------

def normalize_text(text: str) -> str:
    """Collapse all whitespace so layout-only differences are ignored."""
    return re.sub(r"\s+", " ", text or "").strip()


def get_page_text(page) -> str:
    raw_text = page.get_text("text")
    return normalize_text(raw_text)


def get_page_images_hashes(doc, page) -> list[str]:
    """Return sorted list of SHA256 hashes of each image's raw bytes on a page."""
    image_hashes = []
    for img in page.get_images(full=True):
        xref = img[0]
        base_image = doc.extract_image(xref)
        img_bytes = base_image.get("image", b"")
        if img_bytes:
            h = hashlib.sha256(img_bytes).hexdigest()
            image_hashes.append(h)
    image_hashes.sort()
    return image_hashes


def get_page_fonts_info(page) -> list[tuple]:
    """
    Extract font + size + color used in text spans.
    This is a rough proxy for font/style/color differences.
    """
    fonts = set()
    raw = page.get_text("rawdict")
    for block in raw.get("blocks", []):
        if block.get("type") != 0:  # 0 = text block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_name = span.get("font")
                size = span.get("size")
                color = span.get("color")  # integer value
                fonts.add((font_name, size, color))
    return sorted(fonts)


def get_page_visual_hash(page, dpi: int = 144) -> str:
    """
    Render the page to an image and hash the pixels.
    If this matches between PDFs, layout+fonts+colors+graphics are effectively identical.
    """
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return hashlib.sha256(pix.samples).hexdigest()


def analyze_pdf(pdf_path: str):
    """
    Collect comparison info per page:
      - normalized text
      - image hashes
      - font/style info
      - rendered visual hash
    """
    doc = fitz.open(pdf_path)
    pages_info = []

    for page_index in range(len(doc)):
        page = doc[page_index]

        text = get_page_text(page)
        image_hashes = get_page_images_hashes(doc, page)
        fonts_info = get_page_fonts_info(page)
        visual_hash = get_page_visual_hash(page)

        pages_info.append(
            {
                "text": text,
                "image_hashes": image_hashes,
                "fonts": fonts_info,
                "visual_hash": visual_hash,
            }
        )

    doc.close()
    return pages_info


# ---------- Comparison ----------

def compare_pdfs(before_path: str, after_path: str):
    print(f"Analyzing BEFORE migration PDF: {before_path}")
    before_pages = analyze_pdf(before_path)

    print(f"Analyzing AFTER migration PDF:  {after_path}")
    after_pages = analyze_pdf(after_path)

    same = True

    # Page count
    if len(before_pages) != len(after_pages):
        same = False
        print(
            f"\n❌ Page count differs: "
            f"{len(before_pages)} (before) vs {len(after_pages)} (after)"
        )

    page_count = min(len(before_pages), len(after_pages))

    print(f"\nComparing {page_count} page(s) in detail...\n")

    for i in range(page_count):
        b = before_pages[i]
        a = after_pages[i]

        page_num = i + 1
        page_ok = True
        issues = []

        # Text comparison
        if b["text"] != a["text"]:
            page_ok = False
            same = False
            issues.append("TEXT")

        # Images comparison
        if b["image_hashes"] != a["image_hashes"]:
            page_ok = False
            same = False
            issues.append(
                f"IMAGES (before: {len(b['image_hashes'])}, after: {len(a['image_hashes'])})"
            )

        # Fonts comparison
        if b["fonts"] != a["fonts"]:
            page_ok = False
            same = False
            issues.append("FONTS/STYLES/COLORS")

        # Visual hash comparison
        if b["visual_hash"] != a["visual_hash"]:
            page_ok = False
            same = False
            issues.append("VISUAL LAYOUT/RENDER")

        if page_ok:
            print(f"🟩 Page {page_num}: PERFECT MATCH (text, images, fonts, visual)")
        else:
            print(f"🟥 Page {page_num}: Differences in -> {', '.join(issues)}")

    if same:
        print(
            "\n✅ RESULT: PDFs match in text, images, fonts, colors, and rendered layout "
            "(at the chosen DPI)."
        )
    else:
        print(
            "\n❌ RESULT: Differences found between BEFORE and AFTER PDFs.\n"
            "   - TEXT check: normalized content\n"
            "   - IMAGES check: raw bytes hashed\n"
            "   - FONTS/STYLES/COLORS: font name + size + color in spans\n"
            "   - VISUAL LAYOUT/RENDER: full-page bitmap hash (layout/fonts/colors)\n"
        )
        print("If only minor things differ (e.g., tiny color/size changes), they will show here.")


# ---------- Main ----------

def main():
    if len(sys.argv) != 3:
        script = Path(sys.argv[0]).name
        print(f"Usage: python {script} before_migration.pdf after_migration.pdf")
        sys.exit(1)

    before_pdf = sys.argv[1]
    after_pdf = sys.argv[2]
    compare_pdfs(before_pdf, after_pdf)


if __name__ == "__main__":
    main()