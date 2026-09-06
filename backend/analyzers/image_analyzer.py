import io
import os
import hashlib
import struct
import numpy as np
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel

try:
    from PIL import Image, ImageFilter, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

vision_pipeline = None
# Avoid model downloads and heavyweight initialization in serverless functions.
if not os.environ.get("VERCEL"):
    try:
        from transformers import pipeline
        import torch

        print("Loading HuggingFace Deepfake Vision model (umm-maybe/AI-image-detector)... This may take a moment.")
        device = 0 if torch.cuda.is_available() else -1
        vision_pipeline = pipeline("image-classification", model="umm-maybe/AI-image-detector", device=device)
    except ImportError:
        print("Transformers or PyTorch not installed. Falling back to heuristics.")
    except Exception as e:
        print(f"Error loading HuggingFace model: {e}. Falling back to heuristics.")

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class ImageAnalyzer:
    """
    Production-grade image forensic analyzer with multi-signal ensemble:
    1. HuggingFace Neural Net (umm-maybe/AI-image-detector)
    2. Error Level Analysis (ELA)
    3. Deep EXIF metadata parsing
    4. Face detection & symmetry analysis (OpenCV)
    5. Noise consistency analysis
    6. DCT frequency domain analysis (GAN fingerprint detection)
    7. AI generation tool signature scanning
    """

    def analyze(self, image_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        details = []
        file_size = len(image_bytes)
        file_hash = hashlib.md5(image_bytes[:4096]).hexdigest()

        fmt = self._detect_format(image_bytes)

        # Open image with PIL for all analyses
        pil_img = None
        if HAS_PIL and fmt in ["JPEG", "PNG", "WEBP", "BMP", "GIF"]:
            try:
                pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            except Exception:
                pass

        # 1. HuggingFace Neural Network Analysis (primary signal)
        ml_confidence = 0.0
        if vision_pipeline and pil_img:
            try:
                results = vision_pipeline(pil_img)
                artificial_score = 0.0
                for res in results:
                    if res['label'].lower() == 'artificial':
                        artificial_score = res['score']

                ml_confidence = artificial_score

                if artificial_score > 0.8:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Deep Learning model strongly classifies this image as AI-generated/Deepfake (score: {artificial_score:.1%})",
                        confidence=round(artificial_score, 2),
                        severity=RiskLevel.CRITICAL
                    ))
                elif artificial_score > 0.5:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Deep Learning model suspects this image may be AI-generated (score: {artificial_score:.1%})",
                        confidence=round(artificial_score, 2),
                        severity=RiskLevel.HIGH
                    ))
                elif artificial_score > 0.3:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Deep Learning model shows low AI-generation probability (score: {artificial_score:.1%})",
                        confidence=round(artificial_score, 2),
                        severity=RiskLevel.MEDIUM
                    ))
                else:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Deep Learning model classifies this image as likely human-created (score: {artificial_score:.1%})",
                        confidence=round(1.0 - artificial_score, 2),
                        severity=RiskLevel.LOW
                    ))
            except Exception as e:
                print(f"Vision model inference error: {e}")

        # 2. Error Level Analysis (ELA)
        if pil_img and fmt == "JPEG":
            self._error_level_analysis(pil_img, details)

        # 3. Deep EXIF metadata analysis
        self._deep_exif_analysis(image_bytes, fmt, pil_img, details)

        # 4. Face detection & symmetry analysis
        if pil_img and HAS_CV2:
            self._face_analysis(pil_img, details)

        # 5. Noise consistency analysis
        if pil_img:
            self._noise_consistency_analysis(pil_img, details)

        # 6. DCT frequency domain analysis (GAN fingerprint)
        if pil_img:
            self._frequency_domain_analysis(pil_img, details)

        # 7. AI tool signature scanning in metadata
        self._check_ai_signatures(image_bytes, fmt, details)

        # 8. File integrity checks
        self._check_integrity(image_bytes, fmt, filename, details)

        # 9. Resolution and compression analysis
        if pil_img:
            self._resolution_analysis(pil_img, fmt, file_size, details)

        extra_context = {
            "file_size": file_size,
            "format": fmt,
            "file_hash": file_hash,
            "ml_anomaly_score": round(ml_confidence, 2),
            "width": pil_img.width if pil_img else 0,
            "height": pil_img.height if pil_img else 0,
        }

        return details, extra_context

    def _detect_format(self, data: bytes) -> str:
        if data[:3] == b'\xff\xd8\xff': return "JPEG"
        elif data[:8] == b'\x89PNG\r\n\x1a\n': return "PNG"
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP': return "WEBP"
        elif data[:3] == b'GIF': return "GIF"
        elif data[:2] == b'BM': return "BMP"
        return "UNKNOWN"

    # ─── ELA: Error Level Analysis ───────────────────────────────────────
    def _error_level_analysis(self, img: 'Image.Image', details: List[AnalysisDetail]):
        """
        Re-save JPEG at 95% quality, compare with original.
        Manipulated regions show different error levels than original regions.
        """
        try:
            # Re-save at known quality
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            buffer.seek(0)
            resaved = Image.open(buffer).convert('RGB')

            # Compute difference
            orig_arr = np.array(img, dtype=np.float32)
            resaved_arr = np.array(resaved, dtype=np.float32)
            diff = np.abs(orig_arr - resaved_arr)

            # Scale up for visibility
            ela_values = diff * 10.0

            # Analyze ELA statistics
            mean_ela = np.mean(ela_values)
            std_ela = np.std(ela_values)
            max_ela = np.max(ela_values)

            # High variance in ELA = manipulation likely
            # Very low std = consistent compression = likely authentic OR fully synthetic
            # Very high std = inconsistent compression = likely spliced/edited

            if std_ela > 80:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"ELA reveals inconsistent compression levels (σ={std_ela:.1f}) — strong indicator of image splicing or local editing",
                    confidence=min(0.85, 0.5 + std_ela / 200),
                    severity=RiskLevel.HIGH
                ))
            elif std_ela > 50:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"ELA shows moderate compression inconsistency (σ={std_ela:.1f}) — regions may have been edited",
                    confidence=min(0.65, 0.35 + std_ela / 200),
                    severity=RiskLevel.MEDIUM
                ))

            # Check for regions with very different ELA from the mean
            # Split image into 4x4 grid and compare
            h, w = ela_values.shape[:2]
            grid_h, grid_w = h // 4, w // 4
            if grid_h > 10 and grid_w > 10:
                region_means = []
                for gy in range(4):
                    for gx in range(4):
                        region = ela_values[gy*grid_h:(gy+1)*grid_h, gx*grid_w:(gx+1)*grid_w]
                        region_means.append(np.mean(region))

                region_std = np.std(region_means)
                if region_std > 30:
                    details.append(AnalysisDetail(
                        category="Manipulation",
                        finding=f"ELA grid analysis: significant variation across regions (σ={region_std:.1f}) — possible composite/collage",
                        confidence=min(0.75, 0.4 + region_std / 100),
                        severity=RiskLevel.HIGH
                    ))
        except Exception as e:
            print(f"ELA analysis error: {e}")

    # ─── Deep EXIF Analysis ──────────────────────────────────────────────
    def _deep_exif_analysis(self, data: bytes, fmt: str, pil_img, details: List[AnalysisDetail]):
        """
        Comprehensive EXIF/metadata parsing beyond basic checks.
        """
        if fmt == "JPEG":
            has_exif = b'Exif' in data[:1000]
            has_jfif = b'JFIF' in data[:1000]
            has_photoshop = b'Photoshop' in data[:5000]
            has_gimp = b'GIMP' in data[:5000]

            if not has_exif and not has_jfif:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding="No EXIF or JFIF metadata found — metadata has been stripped (common in AI-generated images and edited photos)",
                    confidence=0.55,
                    severity=RiskLevel.MEDIUM
                ))

            if has_photoshop:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding="Adobe Photoshop markers detected — image has been edited with professional tools",
                    confidence=0.7,
                    severity=RiskLevel.HIGH
                ))

            if has_gimp:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding="GIMP editor markers detected — image has been processed with image editing software",
                    confidence=0.65,
                    severity=RiskLevel.HIGH
                ))

            # Try to parse EXIF with PIL
            if pil_img and has_exif:
                try:
                    exif_data = pil_img.getexif()
                    if exif_data:
                        # Check for software tag (306 = Software)
                        software = exif_data.get(305, "")
                        if software:
                            software_lower = str(software).lower()
                            ai_software = ['stable diffusion', 'midjourney', 'dall-e', 'dalle',
                                          'comfyui', 'automatic1111', 'novelai', 'invoke',
                                          'dreamstudio', 'leonardo', 'firefly']
                            for ai_sw in ai_software:
                                if ai_sw in software_lower:
                                    details.append(AnalysisDetail(
                                        category="AI Generation",
                                        finding=f"EXIF Software field contains AI tool: '{software}'",
                                        confidence=0.95,
                                        severity=RiskLevel.CRITICAL
                                    ))
                                    break

                        # Check camera make/model (indicates real photo)
                        make = exif_data.get(271, "")  # Make
                        model = exif_data.get(272, "")  # Model
                        if make and model:
                            details.append(AnalysisDetail(
                                category="Manipulation",
                                finding=f"Camera metadata present: {make} {model} — suggests original photograph",
                                confidence=0.3,
                                severity=RiskLevel.LOW
                            ))
                except Exception:
                    pass

        elif fmt == "PNG":
            has_text = b'tEXt' in data or b'iTXt' in data or b'zTXt' in data
            if not has_text:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding="PNG has no text metadata chunks — common in AI-generated images and screenshots",
                    confidence=0.4,
                    severity=RiskLevel.MEDIUM
                ))

    # ─── Face Detection & Symmetry Analysis ──────────────────────────────
    def _face_analysis(self, img: 'Image.Image', details: List[AnalysisDetail]):
        """
        Detect faces and analyze for deepfake indicators:
        - Symmetry abnormalities
        - Skin texture uniformity (too smooth = synthetic)
        - Edge blending around face boundaries
        """
        try:
            img_array = np.array(img)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            # Load face cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

            if len(faces) == 0:
                return

            for (x, y, w, h) in faces[:3]:  # Analyze up to 3 faces
                face_region = img_array[y:y+h, x:x+w]

                if face_region.shape[0] < 30 or face_region.shape[1] < 30:
                    continue

                # Check face skin texture uniformity
                face_gray = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
                laplacian_var = cv2.Laplacian(face_gray, cv2.CV_64F).var()

                # Very low Laplacian variance = unnaturally smooth skin (common in AI faces)
                if laplacian_var < 100:
                    details.append(AnalysisDetail(
                        category="Deepfake Detection",
                        finding=f"Face detected with unnaturally smooth skin texture (variance={laplacian_var:.0f}) — common in AI-generated faces",
                        confidence=min(0.8, 0.5 + (100 - laplacian_var) / 200),
                        severity=RiskLevel.HIGH
                    ))
                elif laplacian_var < 300:
                    details.append(AnalysisDetail(
                        category="Deepfake Detection",
                        finding=f"Face detected with moderately smooth texture (variance={laplacian_var:.0f}) — may indicate filtering or generation",
                        confidence=0.4,
                        severity=RiskLevel.MEDIUM
                    ))

                # Check face symmetry (deepfakes often are too symmetric or too asymmetric)
                mid_x = face_region.shape[1] // 2
                left_half = face_region[:, :mid_x]
                right_half = cv2.flip(face_region[:, mid_x:2*mid_x], 1)

                if left_half.shape == right_half.shape and left_half.size > 0:
                    symmetry_diff = np.mean(np.abs(left_half.astype(float) - right_half.astype(float)))
                    # Perfect symmetry (< 8) is suspicious (real faces are never perfectly symmetric)
                    if symmetry_diff < 8:
                        details.append(AnalysisDetail(
                            category="Deepfake Detection",
                            finding=f"Face shows unnaturally high symmetry (diff={symmetry_diff:.1f}) — real faces are never this symmetric",
                            confidence=0.7,
                            severity=RiskLevel.HIGH
                        ))

                # Check edge blending around face boundary
                margin = 10
                y1 = max(0, y - margin)
                y2 = min(img_array.shape[0], y + h + margin)
                x1 = max(0, x - margin)
                x2 = min(img_array.shape[1], x + w + margin)
                face_border = img_array[y1:y2, x1:x2]

                if face_border.shape[0] > 20 and face_border.shape[1] > 20:
                    border_gray = cv2.cvtColor(face_border, cv2.COLOR_RGB2GRAY)
                    edges = cv2.Canny(border_gray, 50, 150)
                    edge_density = np.sum(edges > 0) / edges.size

                    # Very low edge density at face boundary = unnatural blending
                    if edge_density < 0.02:
                        details.append(AnalysisDetail(
                            category="Deepfake Detection",
                            finding="Face boundary shows unusually smooth blending with background — possible face swap artifact",
                            confidence=0.6,
                            severity=RiskLevel.HIGH
                        ))

        except Exception as e:
            print(f"Face analysis error: {e}")

    # ─── Noise Consistency Analysis ──────────────────────────────────────
    def _noise_consistency_analysis(self, img: 'Image.Image', details: List[AnalysisDetail]):
        """
        Check if different regions of the image have consistent noise levels.
        Spliced images often have mismatched noise patterns.
        """
        try:
            img_array = np.array(img, dtype=np.float32)

            # Apply high-pass filter to extract noise
            from PIL import ImageFilter
            blurred = img.filter(ImageFilter.GaussianBlur(radius=3))
            blurred_arr = np.array(blurred, dtype=np.float32)
            noise = np.abs(img_array - blurred_arr)

            h, w = noise.shape[:2]
            block_h, block_w = h // 4, w // 4

            if block_h < 20 or block_w < 20:
                return

            # Compute noise level per block
            block_stds = []
            for gy in range(4):
                for gx in range(4):
                    block = noise[gy*block_h:(gy+1)*block_h, gx*block_w:(gx+1)*block_w]
                    block_stds.append(np.std(block))

            noise_variation = np.std(block_stds)
            mean_noise = np.mean(block_stds)

            # High variation in noise across blocks = splicing indicator
            if mean_noise > 0 and noise_variation / mean_noise > 0.5:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Noise analysis reveals inconsistent noise patterns across image regions (CoV={noise_variation/mean_noise:.2f}) — strong splicing indicator",
                    confidence=min(0.8, 0.4 + noise_variation / mean_noise * 0.3),
                    severity=RiskLevel.HIGH
                ))
            elif mean_noise > 0 and noise_variation / mean_noise > 0.3:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Noise analysis shows moderate inconsistency across regions (CoV={noise_variation/mean_noise:.2f}) — possible editing",
                    confidence=0.4,
                    severity=RiskLevel.MEDIUM
                ))

            # Very low overall noise = overly smooth (AI-generated images are often very clean)
            if mean_noise < 2.0:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"Image has unusually low noise levels (mean={mean_noise:.1f}) — AI-generated images tend to be unnaturally clean",
                    confidence=0.5,
                    severity=RiskLevel.MEDIUM
                ))

        except Exception as e:
            print(f"Noise analysis error: {e}")

    # ─── Frequency Domain Analysis (GAN Fingerprint) ─────────────────────
    def _frequency_domain_analysis(self, img: 'Image.Image', details: List[AnalysisDetail]):
        """
        DCT/FFT-based analysis to detect GAN fingerprints.
        GANs leave periodic artifacts in the frequency domain.
        """
        try:
            gray = np.array(img.convert('L'), dtype=np.float32)

            # Resize to standard size for consistent analysis
            target_size = 256
            if gray.shape[0] > target_size and gray.shape[1] > target_size:
                # Center crop
                cy, cx = gray.shape[0] // 2, gray.shape[1] // 2
                half = target_size // 2
                gray = gray[cy-half:cy+half, cx-half:cx+half]

            # Compute 2D FFT
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.abs(f_shift)
            magnitude_log = np.log1p(magnitude)

            # Analyze frequency spectrum for periodicity (GAN fingerprints)
            center_y, center_x = magnitude_log.shape[0] // 2, magnitude_log.shape[1] // 2

            # Compare energy in different frequency bands
            # Low frequency (center), mid frequency, high frequency (edges)
            r_low = min(30, center_y // 4)
            r_mid = min(80, center_y // 2)

            total_energy = np.sum(magnitude_log)
            if total_energy == 0:
                return

            # Create radial masks
            Y, X = np.ogrid[:magnitude_log.shape[0], :magnitude_log.shape[1]]
            dist = np.sqrt((Y - center_y)**2 + (X - center_x)**2)

            low_energy = np.sum(magnitude_log[dist <= r_low])
            mid_energy = np.sum(magnitude_log[(dist > r_low) & (dist <= r_mid)])
            high_energy = np.sum(magnitude_log[dist > r_mid])

            total = low_energy + mid_energy + high_energy
            if total == 0:
                return

            high_ratio = high_energy / total
            mid_ratio = mid_energy / total

            # GANs often have unusual high-frequency energy distribution
            # Real images have smooth falloff; GANs have spikes
            if high_ratio > 0.45:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"Frequency analysis: unusually high energy in high-frequency bands ({high_ratio:.1%}) — possible GAN artifact fingerprint",
                    confidence=min(0.7, 0.35 + high_ratio),
                    severity=RiskLevel.HIGH
                ))

            # Check for periodic peaks (GAN checkerboard artifacts)
            # Look at the magnitude spectrum along rows/columns for periodicity
            mid_row = magnitude_log[center_y, :]
            if len(mid_row) > 20:
                # Compute autocorrelation
                mid_row_norm = mid_row - np.mean(mid_row)
                autocorr = np.correlate(mid_row_norm, mid_row_norm, mode='full')
                autocorr = autocorr[len(autocorr)//2:]  # Only positive lags

                if len(autocorr) > 10 and autocorr[0] > 0:
                    autocorr = autocorr / autocorr[0]  # Normalize
                    # Check for periodic peaks (skip lag 0)
                    peaks = []
                    for i in range(2, len(autocorr) - 1):
                        if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1] and autocorr[i] > 0.3:
                            peaks.append(i)

                    if len(peaks) >= 3:
                        details.append(AnalysisDetail(
                            category="AI Generation",
                            finding=f"Frequency analysis: periodic artifacts detected ({len(peaks)} peaks) — signature of upsampling/GAN generation",
                            confidence=min(0.75, 0.4 + len(peaks) * 0.1),
                            severity=RiskLevel.HIGH
                        ))

        except Exception as e:
            print(f"Frequency analysis error: {e}")

    # ─── AI Tool Signature Scanning ──────────────────────────────────────
    def _check_ai_signatures(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Scan binary data for AI generation tool signatures."""
        ai_tools = [
            b'stable diffusion', b'midjourney', b'dall-e', b'dalle',
            b'comfyui', b'automatic1111', b'novelai', b'invoke-ai',
            b'dreamstudio', b'leonardo.ai', b'firefly', b'stability.ai',
            b'runwayml', b'deepai', b'craiyon', b'hotpot.ai',
            b'artbreeder', b'nightcafe', b'playground-ai',
            b'flux', b'kandinsky', b'imagen',
        ]
        data_lower = data[:50000].lower()
        for tool in ai_tools:
            if tool in data_lower:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"AI generation tool signature found in file data: {tool.decode()}",
                    confidence=0.95,
                    severity=RiskLevel.CRITICAL
                ))
                break

        # Check for common AI generation parameters in metadata
        ai_params = [
            b'sampler', b'cfg_scale', b'steps', b'seed:', b'negative_prompt',
            b'lora', b'checkpoint', b'vae', b'scheduler',
        ]
        param_count = sum(1 for p in ai_params if p in data_lower[:50000])
        if param_count >= 3:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Multiple AI generation parameters found in metadata ({param_count} params: sampler, cfg_scale, etc.)",
                confidence=0.90,
                severity=RiskLevel.CRITICAL
            ))
        elif param_count >= 1:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"AI generation parameter(s) found in metadata ({param_count} matches)",
                confidence=0.6,
                severity=RiskLevel.HIGH
            ))

    # ─── File Integrity ──────────────────────────────────────────────────
    def _check_integrity(self, data: bytes, fmt: str, filename: str, details: List[AnalysisDetail]):
        """Check file extension vs actual format."""
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
                finding=f"File extension '.{ext}' doesn't match actual format '{fmt}' — file may have been renamed to hide its true format",
                confidence=0.7,
                severity=RiskLevel.HIGH
            ))

    # ─── Resolution & Compression Analysis ───────────────────────────────
    def _resolution_analysis(self, img: 'Image.Image', fmt: str, file_size: int, details: List[AnalysisDetail]):
        """Check resolution patterns and compression ratios."""
        w, h = img.size

        # Common AI generation resolutions
        ai_resolutions = [
            (512, 512), (768, 768), (1024, 1024), (2048, 2048),
            (512, 768), (768, 512), (1024, 768), (768, 1024),
            (1024, 1536), (1536, 1024), (896, 1152), (1152, 896),
            (1344, 768), (768, 1344), (832, 1216), (1216, 832),
        ]
        if (w, h) in ai_resolutions:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Image resolution ({w}x{h}) matches common AI generation output sizes",
                confidence=0.4,
                severity=RiskLevel.MEDIUM
            ))

        # Check compression ratio (AI images often have different compression characteristics)
        pixels = w * h * 3  # RGB
        if pixels > 0:
            ratio = file_size / pixels
            # Very high compression ratio for JPEG might indicate re-encoding
            if fmt == "JPEG" and ratio > 0.8:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Unusually low JPEG compression (ratio={ratio:.2f}) — image may have been re-saved multiple times",
                    confidence=0.35,
                    severity=RiskLevel.MEDIUM
                ))


image_analyzer = ImageAnalyzer()
