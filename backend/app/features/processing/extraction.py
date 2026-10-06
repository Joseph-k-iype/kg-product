from io import BytesIO
from pathlib import Path
from pypdf import PdfReader
from docx import Document as WordDocument
from app.adapters.storage import ObjectStore
from app.domain.contracts import ArtifactRef
from app.features.documents.models import Chunk
from sqlalchemy import select


def extract(session, doc):
    if doc.extracted_key and doc.extracted_text is not None:
        return
    data = ObjectStore().get(ArtifactRef(doc.object_key, doc.sha256, doc.sha256))
    extension = Path(doc.name).suffix.lower()
    if doc.data_kind in ("csv", "json", "turtle"):
        text = "\n".join(record["text"] for record in doc.structured_data["records"])
    elif extension == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
    elif extension == ".docx":
        text = "\n".join(p.text for p in WordDocument(BytesIO(data)).paragraphs)
    else:
        text = data.decode("utf-8")
    if not text.strip():
        raise ValueError("No readable text found. Upload a text-based document; scanned PDFs need OCR.")
    artifact = ObjectStore().put(text.encode(), "text/plain")
    doc.extracted_text = text
    doc.extracted_key = artifact.key
    doc.extracted_sha256 = artifact.sha256


def chunk(session, doc):
    if not doc.extracted_text:
        raise ValueError("Extract document text first.")
    if doc.data_kind == "definitions":
        return
    spans = []
    if doc.data_kind in ("csv", "json", "turtle"):
        start = 0
        for record in doc.structured_data["records"]:
            end = start + len(record["text"])
            spans.append((start, end))
            start = end + 1
    else:
        spans = [
            (start, min(start + 800, len(doc.extracted_text)))
            for start in range(0, len(doc.extracted_text), 720)
        ]
    for ordinal, (start, end) in enumerate(spans):
        existing = session.scalars(
            select(Chunk).where(
                Chunk.document_id == doc.id,
                Chunk.ordinal == ordinal,
                Chunk.processing_version == doc.processing_version,
            )
        ).first()
        if not existing:
            session.add(
                Chunk(
                    product_id=doc.product_id,
                    revision_id=doc.revision_id,
                    document_id=doc.id,
                    ordinal=ordinal,
                    start=start,
                    end=end,
                    text=doc.extracted_text[start:end],
                    processing_version=doc.processing_version,
                )
            )
