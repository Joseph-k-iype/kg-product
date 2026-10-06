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
    if extension == ".pdf":
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
    for ordinal, start in enumerate(range(0, len(doc.extracted_text), 720)):
        end = min(start + 800, len(doc.extracted_text))
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
