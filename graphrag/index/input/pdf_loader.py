# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""PDF document loader for GraphRAG.

Includes optional, heuristic PDF→Markdown structuring and page-level metadata capture.
"""

import logging
from importlib import import_module
from pathlib import Path
from typing import Any

import pandas as pd

# Optional runtime imports to avoid hard dependency during linting/build
PDF_AVAILABLE = True
try:
    PyPDF2_mod: Any | None = import_module("PyPDF2")
    fitz_mod: Any | None = import_module("fitz")  # PyMuPDF
except Exception:  # noqa: BLE001 - runtime optional dependency
    PyPDF2_mod = None
    fitz_mod = None
    PDF_AVAILABLE = False

from graphrag.index.input.util import process_data_columns
from graphrag.config.models.input_config import InputConfig

logger = logging.getLogger(__name__)


class PDFLoader:
    """PDF document loader with multiple extraction strategies and optional Markdown structuring.

    This loader extracts page-wise text and basic metadata, and can optionally attempt
    a lightweight Markdown heading inference by using simple heuristics when PyMuPDF
    provides style information. For robust PDF→Markdown conversion, users should
    consider dedicated tools (e.g., pymupdf4llm/unstructured). Here we provide a
    pragmatic PoC suitable for downstream chunking and section-aware search.
    """
    
    def __init__(self, extraction_method: str = "pymupdf", to_markdown: bool = False):
        """
        Initialize PDF loader.
        
        Args:
            extraction_method: Method to use for PDF text extraction
                             - "pymupdf": Use PyMuPDF (fitz) for better text extraction
                             - "pypdf2": Use PyPDF2 for basic text extraction
        """
        if not PDF_AVAILABLE:
            msg = (
                "PDF parsing requires optional dependencies. "
                "Install with: pip install PyPDF2 PyMuPDF"
            )
            raise ImportError(msg)
        
        self.extraction_method = extraction_method
        self.to_markdown = to_markdown
    
    def extract_text_pymupdf(self, pdf_path: str) -> tuple[str, dict[str, Any]]:
        """Extract text using PyMuPDF (better quality). Optionally infer Markdown headings."""
        if fitz_mod is None:
            raise RuntimeError("PyMuPDF not available, cannot use 'pymupdf' method")
        doc = fitz_mod.open(pdf_path)
        text_parts = []
        metadata = {
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
        }
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            if self.to_markdown:
                # Use blocks and font sizes to infer headings when available
                try:
                    blocks = page.get_text("blocks", flags=fitz_mod.TEXTFLAGS_TEXT)
                    # Heuristic: compute per-page max font size via spans from "dict"
                    page_dict = page.get_text("dict")
                    font_sizes = [
                        span.get("size", 0)
                        for block in page_dict.get("blocks", [])
                        for line in block.get("lines", [])
                        for span in line.get("spans", [])
                        if isinstance(span.get("size", 0), (int, float))
                    ]
                    max_size = max(font_sizes) if font_sizes else 0

                    md_lines: list[str] = [f"[Page {page_num + 1}]\n"]
                    for block_tuple in blocks:
                        _x1, _y1, _x2, _y2, btext, *_rest = block_tuple
                        btext = (btext or "").strip()
                        if not btext:
                            continue
                        # Basic heading inference by first span size ratio
                        heading_level: int | None = None
                        first_span_size: float | None = None
                        found = False
                        for blk in page_dict.get("blocks", []):
                            if found:
                                break
                            for line in blk.get("lines", []):
                                if found:
                                    break
                                for span in line.get("spans", []):
                                    st = (span.get("text") or "").strip()
                                    if st and st in btext:
                                        first_span_size = span.get("size", 0)
                                        found = True
                                        break

                        if max_size and first_span_size and (first_span_size / max_size) >= 0.95:
                            heading_level = 1
                        elif max_size and first_span_size and (first_span_size / max_size) >= 0.85:
                            heading_level = 2

                        if heading_level:
                            md_lines.append(f"{'#' * heading_level} {btext}")
                        else:
                            md_lines.append(btext)

                    text_parts.append("\n".join(md_lines))
                except Exception as err:  # fallback to plain text
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(f"[Page {page_num + 1}]\n{text}")
                    logger.warning("Heuristic markdown inference failed on %s page %d: %s", pdf_path, page_num + 1, err)
            else:
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")
        
        doc.close()
        return "\n\n".join(text_parts), metadata
    
    def extract_text_pypdf2(self, pdf_path: str) -> tuple[str, dict[str, Any]]:
        """Extract text using PyPDF2 (basic extraction)."""
        if PyPDF2_mod is None:
            raise RuntimeError("PyPDF2 not available, cannot use 'pypdf2' method")
        with Path(pdf_path).open("rb") as file:
            pdf_reader = PyPDF2_mod.PdfReader(file)
            text_parts = []
            
            metadata = {
                "page_count": len(pdf_reader.pages),
                "title": "",
                "author": "",
                "creation_date": "",
                "modification_date": "",
            }
            
            # Extract metadata if available
            if pdf_reader.metadata:
                metadata.update({
                    "title": pdf_reader.metadata.get("/Title", ""),
                    "author": pdf_reader.metadata.get("/Author", ""),
                    "creation_date": str(pdf_reader.metadata.get("/CreationDate", "")),
                    "modification_date": str(pdf_reader.metadata.get("/ModDate", "")),
                })
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")
        
        return "\n\n".join(text_parts), metadata
    
    def extract_text(self, pdf_path: str) -> tuple[str, dict[str, Any]]:
        """Extract text from PDF using the configured method."""
        try:
            if self.extraction_method == "pymupdf":
                return self.extract_text_pymupdf(pdf_path)
            return self.extract_text_pypdf2(pdf_path)
        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to extract text from %s: %s", pdf_path, err)
            return "", {}


async def load_pdf(
    config: InputConfig,
    storage: Any,
) -> pd.DataFrame:
    """Load PDF inputs from a directory using util.load_files."""
    from graphrag.index.input.util import load_files, process_data_columns

    async def _load_single_pdf(path: str, group: dict[str, Any] | None = None) -> pd.DataFrame:
        if group is None:
            group = {}
        loader = PDFLoader(extraction_method="pymupdf", to_markdown=True)
        try:
            text, metadata = loader.extract_text(path)
            if not text.strip():
                logger.warning("No text extracted from PDF: %s", path)
                return pd.DataFrame()

            document_data: dict[str, Any] = {
                **group,
                "text": text,
                "title": metadata.get("title") or Path(path).stem,
                "creation_date": metadata.get("creation_date", ""),
                "metadata": {
                    **metadata,
                    "file_type": "pdf",
                    "file_path": path,
                    "extraction_method": loader.extraction_method,
                    "markdown": loader.to_markdown,
                },
            }
            df = pd.DataFrame([document_data])
            df = process_data_columns(df, config, path)
            return df
        except Exception as err:  # noqa: BLE001
            logger.exception("Error loading PDF %s", path)
            return pd.DataFrame()

    return await load_files(_load_single_pdf, config, storage)