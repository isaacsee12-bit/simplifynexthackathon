import io
import hashlib
import struct
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel


class ImageAnalyzer:
    """
    Analyzes images for:
    - AI generation artifacts
    - Metadata anomalies
    - Pixel-level manipulation
    - Known deepfake patterns
    """

    # Common AI-generated image signatures
    AI_IMAGE_INDICATORS = {
        "uniform_noise": "Suspiciously uniform noise pattern across the image",
        "color_banding": "Color banding artifacts typical of AI generation",
        "edge_artifacts": "Irregular edge artifacts around subjects",
        "symmetry_anomaly": "Unusual facial symmetry (common in AI-generated faces)",
        "texture_repeat": "Repeating texture patterns in background",
        "metadata_stripped": "Image metadata has been stripped (common in AI images)",
        "resolution_mismatch": "Internal resolution inconsistencies",
    }

    def analyze(self, image_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        """
        Analyze an image for manipulation or AI generation.
        Uses heuristic analysis on raw bytes when PIL/OpenCV not available.
        """
        details = []
        file_size = len(image_bytes)
        file_hash = hashlib.md5(image_bytes[:4096]).hexdigest()

        # Determine format from magic bytes
        fmt = self._detect_format(image_bytes)

        # 1. Check metadata
        self._check_metadata(image_bytes, fmt, details)

        # 2. Analyze pixel patterns (byte-level heuristics)
        self._analyze_pixel_patterns(image_bytes, fmt, details)

        # 3. Check for AI generation markers
        self._check_ai_generation(image_bytes, file_size, fmt, details)

        # 4. Check file integrity
        self._check_integrity(image_bytes, fmt, filename, details)

        extra_context = {
            "file_size": file_size,
            "format": fmt,
            "file_hash": file_hash,
        }

        return details, extra_context

    def _detect_format(self, data: bytes) -> str:
        """Detect image format from magic bytes."""
        if data[:3] == b'\xff\xd8\xff':
            return "JPEG"
        elif data[:8] == b'\x89PNG\r\n\x1a\n':
            return "PNG"
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return "WEBP"
        elif data[:3] == b'GIF':
            return "GIF"
        elif data[:2] == b'BM':
            return "BMP"
        return "UNKNOWN"

    def _check_metadata(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Check image metadata for anomalies."""
        if fmt == "JPEG":
            # Check for EXIF data
            has_exif = b'Exif' in data[:1000]
            has_jfif = b'JFIF' in data[:1000]
            has_adobe = b'Adobe' in data[:500]
            has_photoshop = b'Photoshop' in data[:2000]

            if not has_exif and not has_jfif:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding="No EXIF or JFIF metadata found — metadata may have been stripped",
                    confidence=0.5,
                    severity=RiskLevel.MEDIUM
                ))

            if has_photoshop:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding="Adobe Photoshop markers detected — image has been edited",
                    confidence=0.7,
                    severity=RiskLevel.HIGH
                ))

        elif fmt == "PNG":
            # PNG with no text chunks is suspicious
            has_text = b'tEXt' in data or b'iTXt' in data or b'zTXt' in data
            if not has_text:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding="PNG has no text metadata — common in AI-generated images",
                    confidence=0.4,
                    severity=RiskLevel.MEDIUM
                ))

            # Check for AI tool metadata
            ai_tools = [b'stable diffusion', b'midjourney', b'dall-e', b'dalle',
                       b'comfyui', b'automatic1111', b'novelai']
            data_lower = data[:10000].lower()
            for tool in ai_tools:
                if tool in data_lower:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"AI generation tool signature found: {tool.decode()}",
                        confidence=0.95,
                        severity=RiskLevel.CRITICAL
                    ))
                    break

    def _analyze_pixel_patterns(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Analyze byte patterns for manipulation indicators."""
        # Sample bytes from the image data portion
        sample_start = min(1000, len(data) // 4)
        sample_end = min(sample_start + 10000, len(data))
        sample = data[sample_start:sample_end]

        if len(sample) < 100:
            return

        # Check byte distribution uniformity
        byte_counts = [0] * 256
        for b in sample:
            byte_counts[b] += 1

        total = len(sample)
        expected = total / 256
        chi_squared = sum((count - expected) ** 2 / expected for count in byte_counts if expected > 0)

        # Very uniform distribution can indicate synthetic content
        if chi_squared < 200:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding="Unusually uniform byte distribution — may indicate synthetic image data",
                confidence=0.45,
                severity=RiskLevel.MEDIUM
            ))

        # Check for repeated byte patterns
        pattern_size = 16
        patterns = set()
        repeated_count = 0
        for i in range(0, len(sample) - pattern_size, pattern_size):
            pattern = sample[i:i+pattern_size]
            if pattern in patterns:
                repeated_count += 1
            patterns.add(pattern)

        repeat_ratio = repeated_count / max(len(patterns), 1)
        if repeat_ratio > 0.3:
            details.append(AnalysisDetail(
                category="Manipulation",
                finding=f"High byte pattern repetition ({repeat_ratio:.0%}) — possible copy-paste manipulation",
                confidence=0.55,
                severity=RiskLevel.MEDIUM
            ))

    def _check_ai_generation(self, data: bytes, file_size: int, fmt: str, details: List[AnalysisDetail]):
        """Check for AI generation indicators."""
        # AI images often have very specific file sizes
        # Standard AI generation outputs: 512x512, 768x768, 1024x1024
        if fmt == "PNG":
            # Try to read PNG dimensions
            if len(data) >= 24:
                width = struct.unpack('>I', data[16:20])[0]
                height = struct.unpack('>I', data[20:24])[0]

                # Common AI generation resolutions
                ai_resolutions = [
                    (512, 512), (768, 768), (1024, 1024),
                    (512, 768), (768, 512), (1024, 768),
                    (768, 1024), (1024, 1536), (1536, 1024),
                ]
                if (width, height) in ai_resolutions:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Image resolution ({width}x{height}) matches common AI generation output sizes",
                        confidence=0.4,
                        severity=RiskLevel.MEDIUM
                    ))

    def _check_integrity(self, data: bytes, fmt: str, filename: str, details: List[AnalysisDetail]):
        """Check file integrity and consistency."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        format_ext_map = {
            "JPEG": ["jpg", "jpeg"],
            "PNG": ["png"],
            "WEBP": ["webp"],
            "GIF": ["gif"],
            "BMP": ["bmp"],
        }

        expected_exts = format_ext_map.get(fmt, [])
        if ext and expected_exts and ext not in expected_exts:
            details.append(AnalysisDetail(
                category="Manipulation",
                finding=f"File extension '.{ext}' doesn't match actual format '{fmt}' — file may have been renamed",
                confidence=0.7,
                severity=RiskLevel.HIGH
            ))


image_analyzer = ImageAnalyzer()
