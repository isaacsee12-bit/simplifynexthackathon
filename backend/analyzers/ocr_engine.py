import re
from typing import Optional


class OCREngine:
    """
    OCR engine for extracting text from screenshots and images.
    Uses a fallback heuristic when Tesseract is not installed.
    """

    def __init__(self):
        self.tesseract_available = False
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
        except Exception:
            pass

    def extract_text(self, image_bytes: bytes) -> Optional[str]:
        """
        Extract text from image bytes.
        Uses Tesseract if available, otherwise returns None.
        """
        if self.tesseract_available:
            return self._extract_with_tesseract(image_bytes)
        return self._extract_fallback(image_bytes)

    def _extract_with_tesseract(self, image_bytes: bytes) -> Optional[str]:
        """Extract text using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            import io

            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip() if text.strip() else None
        except Exception:
            return None

    def _extract_fallback(self, image_bytes: bytes) -> Optional[str]:
        """
        Fallback: attempt to find readable text in image binary data.
        This catches text in metadata, embedded data, or text-heavy formats.
        """
        try:
            # Try to find readable ASCII strings in the first 500KB of image data
            text_pattern = re.compile(rb'[\x20-\x7e]{10,}')
            matches = text_pattern.findall(image_bytes[:500000])
            if matches:
                # Filter out obvious binary/metadata strings
                readable = []
                skip_patterns = [
                    b'IHDR', b'IDAT', b'IEND', b'Adobe', b'Exif',
                    b'<?xml', b'<rdf:', b'xmlns', b'http://',
                ]
                for match in matches:
                    if not any(skip in match for skip in skip_patterns):
                        decoded = match.decode('ascii', errors='ignore')
                        if len(decoded) > 15 and ' ' in decoded:
                            readable.append(decoded)
                if readable:
                    return '\n'.join(readable[:10])
        except Exception:
            pass
        return None


ocr_engine = OCREngine()
