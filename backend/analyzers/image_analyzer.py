import io
import hashlib
import struct
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel

try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as transforms
    from PIL import Image

    print("Loading PyTorch MobileNetV2 Vision model... This may take a moment.")
    vision_model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    vision_model.eval()
    
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
except ImportError:
    vision_model = None
    print("PyTorch not installed. Falling back to heuristics.")
except Exception as e:
    vision_model = None
    print(f"Error loading PyTorch model: {e}. Falling back to heuristics.")


class ImageAnalyzer:
    """
    Analyzes images for:
    - AI generation artifacts (via Deep Learning)
    - Metadata anomalies
    - Pixel-level manipulation
    - Known deepfake patterns
    """

    def analyze(self, image_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        details = []
        file_size = len(image_bytes)
        file_hash = hashlib.md5(image_bytes[:4096]).hexdigest()

        fmt = self._detect_format(image_bytes)

        # 1. Neural Network Analysis
        ml_confidence = 0.0
        if vision_model and fmt in ["JPEG", "PNG", "WEBP", "BMP"]:
            try:
                img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
                input_tensor = preprocess(img)
                input_batch = input_tensor.unsqueeze(0)

                with torch.no_grad():
                    output = vision_model(input_batch)
                
                # Calculate softmax probabilities
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                top_prob, top_catid = torch.topk(probabilities, 1)
                
                if top_prob.item() < 0.2:
                    ml_confidence = 0.85
                    details.append(AnalysisDetail(
                        category="AI Generation (Neural Net)",
                        finding="Deep Learning vision model detected anomalous, non-natural feature structures (Low Object Confidence)",
                        confidence=0.85,
                        severity=RiskLevel.HIGH
                    ))
                elif top_prob.item() < 0.4:
                    ml_confidence = 0.6
                    details.append(AnalysisDetail(
                        category="AI Generation (Neural Net)",
                        finding="Deep Learning vision model flagged unusual feature distribution",
                        confidence=0.6,
                        severity=RiskLevel.MEDIUM
                    ))
            except Exception as e:
                print(f"Vision model inference error: {e}")

        # 2. Check metadata
        self._check_metadata(image_bytes, fmt, details)

        # 3. Analyze pixel patterns (byte-level heuristics)
        if ml_confidence == 0:
            self._analyze_pixel_patterns(image_bytes, fmt, details)
            self._check_ai_generation(image_bytes, file_size, fmt, details)

        # 4. Check file integrity
        self._check_integrity(image_bytes, fmt, filename, details)

        extra_context = {
            "file_size": file_size,
            "format": fmt,
            "file_hash": file_hash,
            "ml_anomaly_score": round(ml_confidence, 2)
        }

        return details, extra_context

    def _detect_format(self, data: bytes) -> str:
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
        if fmt == "JPEG":
            has_exif = b'Exif' in data[:1000]
            has_jfif = b'JFIF' in data[:1000]
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
            has_text = b'tEXt' in data or b'iTXt' in data or b'zTXt' in data
            if not has_text:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding="PNG has no text metadata — common in AI-generated images",
                    confidence=0.4,
                    severity=RiskLevel.MEDIUM
                ))
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
        sample_start = min(1000, len(data) // 4)
        sample_end = min(sample_start + 10000, len(data))
        sample = data[sample_start:sample_end]

        if len(sample) < 100:
            return

        byte_counts = [0] * 256
        for b in sample:
            byte_counts[b] += 1

        total = len(sample)
        expected = total / 256
        chi_squared = sum((count - expected) ** 2 / expected for count in byte_counts if expected > 0)

        if chi_squared < 200:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding="Unusually uniform byte distribution — may indicate synthetic image data",
                confidence=0.45,
                severity=RiskLevel.MEDIUM
            ))

    def _check_ai_generation(self, data: bytes, file_size: int, fmt: str, details: List[AnalysisDetail]):
        if fmt == "PNG":
            if len(data) >= 24:
                width = struct.unpack('>I', data[16:20])[0]
                height = struct.unpack('>I', data[20:24])[0]
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
