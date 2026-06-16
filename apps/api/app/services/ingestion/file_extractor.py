"""Local file text extraction."""

from pathlib import Path


class FileExtractor:
    """Extract text from supported local file formats."""

    async def extract(self, file_path: Path, content_type: str | None = None) -> str:
        suffix = file_path.suffix.lower()
        if suffix in {".txt", ".md"} or (content_type and content_type.startswith("text/")):
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf" or content_type == "application/pdf":
            return self._extract_pdf(file_path)
        raise ValueError(f"Unsupported file type: {suffix or content_type}")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using pypdfium2 when available."""
        try:
            import pypdfium2 as pdfium
        except Exception as exc:
            raise ValueError("PDF extraction requires pypdfium2") from exc

        document = pdfium.PdfDocument(str(file_path))
        pages = []
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_range())
            textpage.close()
            page.close()
        document.close()
        return "\n\n".join(page.strip() for page in pages if page.strip())
