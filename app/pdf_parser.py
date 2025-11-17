"""Utilities for parsing uploaded PDF resumes."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional

from markitdown import MarkItDown


class ResumeParsingError(RuntimeError):
    """Raised when a resume cannot be parsed."""


class ResumeParser:
    """Thin wrapper around MarkItDown to parse PDF bytes once per process."""

    def __init__(self) -> None:
        self._converter = MarkItDown()
        print("[ResumeParser] Initialized MarkItDown converter.")

    def convert_pdf_bytes(self, data: bytes, *, file_name: Optional[str] = None) -> str:
        """Convert PDF bytes into markdown/plain text."""
        if not data:
            raise ResumeParsingError("Uploaded resume is empty.")

        printable_name = file_name or "uploaded_resume.pdf"
        received_message = (
            f"[ResumeParser] {datetime.utcnow().isoformat()} - "
            f"Received {len(data)} bytes for {printable_name}."
        )
        print(received_message)

        try:
            result = self._converter.convert(BytesIO(data))
            print(
                f"[ResumeParser] {datetime.utcnow().isoformat()} - "
                f"MarkItDown conversion finished for {printable_name}. "
                f"Result type: {type(result)}"
            )
        except Exception as exception:  # pragma: no cover - library level errors
            print(
                f"[ResumeParser] {datetime.utcnow().isoformat()} - "
                f"MarkItDown conversion failed for {printable_name}: {exception}"
            )
            raise ResumeParsingError("Failed to parse the PDF resume.") from exception

        markdown = (result.markdown or "").strip()
        if not markdown:
            print(
                f"[ResumeParser] {datetime.utcnow().isoformat()} - "
                f"MarkItDown returned empty content for {printable_name}."
            )
            raise ResumeParsingError(
                f"Unable to extract readable text from {file_name or 'resume'}."
            )

        print(
            f"[ResumeParser] {datetime.utcnow().isoformat()} - "
            f"Markdown extraction succeeded for {printable_name}. "
            f"Characters: {len(markdown)}"
        )
        return markdown


resume_parser = ResumeParser()
