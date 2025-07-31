# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""PDF document loader for GraphRAG."""

import logging
from typing import Any
import pandas as pd
from pathlib import Path

try:
    import PyPDF2
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from graphrag.index.input.util import process_data_columns
from graphrag.config.models.input_config import InputConfig

logger = logging.getLogger(__name__)


class PDFLoader:
    """PDF document loader with multiple extraction strategies."""
    
    def __init__(self, extraction_method: str = "pymupdf"):
        """
        Initialize PDF loader.
        
        Args:
            extraction_method: Method to use for PDF text extraction
                             - "pymupdf": Use PyMuPDF (fitz) for better text extraction
                             - "pypdf2": Use PyPDF2 for basic text extraction
        """
        if not PDF_AVAILABLE:
            raise ImportError(
                "PDF parsing requires additional dependencies. "
                "Install with: pip install PyPDF2 PyMuPDF"
            )
        
        self.extraction_method = extraction_method
    
    def extract_text_pymupdf(self, pdf_path: str) -> tuple[str, dict[str, Any]]:
        """Extract text using PyMuPDF (better quality)."""
        doc = fitz.open(pdf_path)
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
            text = page.get_text()
            if text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{text}")
        
        doc.close()
        return "\n\n".join(text_parts), metadata
    
    def extract_text_pypdf2(self, pdf_path: str) -> tuple[str, dict[str, Any]]:
        """Extract text using PyPDF2 (basic extraction)."""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
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
            else:
                return self.extract_text_pypdf2(pdf_path)
        except Exception as e:
            logger.warning(f"Failed to extract text from {pdf_path}: {e}")
            return "", {}


async def load_pdf(
    file_path: str,
    group: dict[str, Any] | None = None,
    config: InputConfig | None = None,
) -> pd.DataFrame:
    """Load a PDF file and return a DataFrame with document data."""
    loader = PDFLoader(extraction_method="pymupdf")
    
    try:
        text, metadata = loader.extract_text(file_path)
        
        if not text.strip():
            logger.warning(f"No text extracted from PDF: {file_path}")
            return pd.DataFrame()
        
        # Create document record
        document_data = {
            "text": text,
            "title": metadata.get("title") or Path(file_path).stem,
            "creation_date": metadata.get("creation_date", ""),
            "metadata": {
                **metadata,
                "file_type": "pdf",
                "file_path": file_path,
                "extraction_method": loader.extraction_method,
            }
        }
        
        df = pd.DataFrame([document_data])
        
        # Apply standard column processing if config is provided
        if config:
            df = process_data_columns(df, config, file_path)
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading PDF {file_path}: {e}")
        return pd.DataFrame() 