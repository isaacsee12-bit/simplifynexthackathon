from typing import Optional


class OCREngine:
    """Extract visible text only; binary metadata is not OCR evidence."""

    def __init__(self):
        self.tesseract_available = False
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
        except Exception:
            pass

    def extract_text(self, image_bytes: bytes) -> Optional[str]:
        if self.tesseract_available:
            return self._extract_with_tesseract(image_bytes)
        return None

    def _extract_with_tesseract(self, image_bytes: bytes) -> Optional[str]:
        try:
            import io
            import pytesseract
            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as image:
                text = pytesseract.image_to_string(image, timeout=10)
            return text.strip() or None
        except Exception:
            return None


ocr_engine = OCREngine()
