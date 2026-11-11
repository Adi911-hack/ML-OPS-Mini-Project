
from pathlib import Path
import json
import re
import pymupdf

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "documents"
OUTPUT_FILE = BASE_DIR / "chunks.json"


def clean_text(text):
    text = "".join(
        chr(ord(c) - 0xF000) if 0xF020 <= ord(c) <= 0xF07E else c
        for c in text
    )

    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*[AP]M", " ", text)
    text = re.sub(r"Find low fares and book now", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_text(text, chunk_size=1000, overlap=200):
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk size or overlap")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def process_pdf(file_path):
    results = []

    with pymupdf.open(file_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = clean_text(page.get_text("text"))

            if not text:
                print(f"Warning: No text on page {page_number} of {file_path.name}")
                continue

            chunks = split_text(text)

            for index, chunk in enumerate(chunks, start=1):
                results.append({
                    "id": f"{file_path.stem}_p{page_number}_c{index}",
                    "source": file_path.name,
                    "page": page_number,
                    "chunk": index,
                    "text": chunk
                })

    return results


def main():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(DOCUMENTS_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    all_chunks = []

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")

        chunks = process_pdf(pdf_file)
        all_chunks.extend(chunks)

        print(f"Created {len(chunks)} chunks")

    if not all_chunks:
        print("No text extracted from PDFs.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(all_chunks, file, indent=2, ensure_ascii=False)

    print(f"Total chunks: {len(all_chunks)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
