import hashlib
import struct
import tempfile
import os
import numpy as np
from typing import List, Tuple
from models.schemas import AnalysisDetail, FrameAnalysis, RiskLevel

try:
    import cv2
    from PIL import Image
    from analyzers.image_analyzer import vision_pipeline
    HAS_CV2_AND_MODEL = True if vision_pipeline else False
except ImportError:
    HAS_CV2_AND_MODEL = False
    cv2 = None


class VideoAnalyzer:
    """
    Production-grade video deepfake analyzer:
    1. Multi-frame sampling with HF model (up to 15 frames)
    2. Face detection & temporal consistency
    3. Inter-frame consistency analysis (lighting, color shifts)
    4. Audio track presence check
    5. Container/compression analysis
    6. Motion analysis for unnatural patterns
    """

    MAX_SAMPLE_FRAMES = 15  # Analyze up to 15 frames

    def analyze(self, video_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        details = []
        file_size = len(video_bytes)
        file_hash = hashlib.md5(video_bytes[:8192]).hexdigest()
        fmt = self._detect_format(video_bytes)

        frame_analyses = []
        deepfake_count = 0
        total_frames = 0
        fps = 0
        duration = 0
        width = 0
        height = 0

        temp_path = None

        if HAS_CV2_AND_MODEL or cv2:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                    temp_video.write(video_bytes)
                    temp_path = temp_video.name

                cap = cv2.VideoCapture(temp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = total_frames / fps if fps > 0 else 0

                if total_frames > 0:
                    # 1. Sample and analyze frames with HF model
                    num_samples = min(total_frames, self.MAX_SAMPLE_FRAMES)
                    step = max(1, total_frames // num_samples)

                    sampled_frames = []  # Store frames for inter-frame analysis
                    frame_brightnesses = []
                    frame_colors = []

                    for i in range(num_samples):
                        frame_num = i * step
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                        ret, frame = cap.read()

                        if not ret:
                            continue

                        # Store frame data for temporal analysis
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        frame_brightnesses.append(np.mean(gray))
                        frame_colors.append(np.mean(frame, axis=(0, 1)))
                        sampled_frames.append(frame)

                        # Run HF model on frame
                        artificial_score = 0.0
                        if vision_pipeline:
                            try:
                                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                                results = vision_pipeline(img)
                                for res in results:
                                    if res['label'].lower() == 'artificial':
                                        artificial_score = res['score']
                            except Exception as e:
                                print(f"Frame ML error: {e}")

                        is_anomalous = artificial_score > 0.5
                        if is_anomalous:
                            deepfake_count += 1

                        frame_analyses.append(FrameAnalysis(
                            frame_number=frame_num,
                            is_deepfake=is_anomalous,
                            deepfake_probability=round(artificial_score, 3),
                            details=("Neural detector unavailable; frame sampled for temporal analysis only."
                                     if not vision_pipeline else
                                     f"AI-generated features detected (score: {artificial_score:.1%})" if is_anomalous
                                     else f"Frame appears natural (score: {artificial_score:.1%})")
                        ))

                    # 2. Inter-frame temporal consistency analysis
                    if len(sampled_frames) >= 3:
                        self._temporal_consistency_analysis(
                            sampled_frames, frame_brightnesses, frame_colors, details
                        )

                    # 3. Face temporal consistency across frames
                    if len(sampled_frames) >= 3 and cv2:
                        self._face_temporal_analysis(sampled_frames, details)

                cap.release()

            except Exception as e:
                print(f"Video analysis error: {e}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        # 4. Report frame-level results
        if not vision_pipeline:
            details.append(AnalysisDetail(
                category="System Error",
                finding="Neural video detector unavailable. Temporal and container analysis only; frame probabilities are not model predictions.",
                confidence=1.0,
                severity=RiskLevel.MEDIUM,
            ))
        elif len(frame_analyses) > 0:
            deepfake_ratio = deepfake_count / len(frame_analyses)
            avg_score = np.mean([fa.deepfake_probability for fa in frame_analyses])

            if deepfake_ratio > 0.7:
                details.append(AnalysisDetail(
                    category="Deepfake Detection",
                    finding=f"AI model flagged {deepfake_count}/{len(frame_analyses)} sampled frames as AI-generated (avg score: {avg_score:.1%})",
                    confidence=round(0.6 + deepfake_ratio * 0.35, 2),
                    severity=RiskLevel.CRITICAL
                ))
            elif deepfake_ratio > 0.4:
                details.append(AnalysisDetail(
                    category="Deepfake Detection",
                    finding=f"AI model flagged {deepfake_count}/{len(frame_analyses)} sampled frames as potentially AI-generated (avg: {avg_score:.1%})",
                    confidence=round(0.4 + deepfake_ratio * 0.4, 2),
                    severity=RiskLevel.HIGH
                ))
            elif deepfake_ratio > 0.0:
                details.append(AnalysisDetail(
                    category="Deepfake Detection",
                    finding=f"AI model flagged {deepfake_count}/{len(frame_analyses)} sampled frames as suspicious (avg: {avg_score:.1%})",
                    confidence=round(0.2 + deepfake_ratio * 0.3, 2),
                    severity=RiskLevel.MEDIUM
                ))
            else:
                details.append(AnalysisDetail(
                    category="Deepfake Detection",
                    finding=f"All {len(frame_analyses)} sampled frames appear natural (avg AI score: {avg_score:.1%})",
                    confidence=round(1.0 - avg_score, 2),
                    severity=RiskLevel.LOW
                ))

        # 5. Container/compression analysis
        self._check_compression(video_bytes, fmt, details)

        # 6. Resolution check
        if width > 0 and height > 0:
            self._resolution_check(width, height, details)

        # 7. Audio track check
        self._audio_track_check(video_bytes, fmt, details)

        extra_context = {
            "total_frames_estimated": total_frames,
            "deepfake_frames_sampled": deepfake_count,
            "total_frames_sampled": len(frame_analyses),
            "format": fmt,
            "file_size": file_size,
            "fps": round(fps, 1),
            "duration_seconds": round(duration, 1),
            "resolution": f"{width}x{height}",
            "frame_analyses": frame_analyses,
        }

        return details, extra_context

    def _detect_format(self, data: bytes) -> str:
        if data[:4] in [b'\x00\x00\x00\x1c', b'\x00\x00\x00\x20'] or data[4:8] == b'ftyp':
            return "MP4"
        elif data[:4] == b'RIFF' and data[8:12] == b'AVI ':
            return "AVI"
        elif data[:4] == b'\x1a\x45\xdf\xa3':
            return "WEBM/MKV"
        elif data[:3] == b'\x00\x00\x01':
            return "MPEG"
        return "UNKNOWN"

    # ─── Temporal Consistency Analysis ────────────────────────────────────
    def _temporal_consistency_analysis(self, frames, brightnesses, colors, details: List[AnalysisDetail]):
        """
        Check for unnatural temporal jumps in brightness and color.
        Deepfakes often have frame-to-frame inconsistencies.
        """
        try:
            if len(brightnesses) < 3:
                return

            bright_arr = np.array(brightnesses)
            bright_diffs = np.abs(np.diff(bright_arr))

            # Check for sudden brightness jumps
            bright_mean_diff = np.mean(bright_diffs)
            bright_max_diff = np.max(bright_diffs)

            if bright_max_diff > 30 and bright_mean_diff < 10:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Sudden brightness jump detected between frames (max Δ={bright_max_diff:.1f}, mean Δ={bright_mean_diff:.1f}) — possible splice point",
                    confidence=min(0.7, 0.3 + bright_max_diff / 100),
                    severity=RiskLevel.HIGH
                ))

            # Check color consistency
            if len(colors) >= 3:
                color_arr = np.array(colors)
                color_diffs = np.sqrt(np.sum(np.diff(color_arr, axis=0)**2, axis=1))
                color_max_diff = np.max(color_diffs)
                color_mean_diff = np.mean(color_diffs)

                if color_max_diff > 20 and color_mean_diff < 8:
                    details.append(AnalysisDetail(
                        category="Manipulation",
                        finding=f"Sudden color shift detected between frames (max Δ={color_max_diff:.1f}) — possible editing or face swap boundary",
                        confidence=min(0.65, 0.3 + color_max_diff / 50),
                        severity=RiskLevel.HIGH
                    ))

        except Exception as e:
            print(f"Temporal consistency error: {e}")

    # ─── Face Temporal Analysis ──────────────────────────────────────────
    def _face_temporal_analysis(self, frames, details: List[AnalysisDetail]):
        """
        Track faces across frames and check for:
        - Face size/position jitter (deepfakes often have unstable face tracking)
        - Disappearing/appearing faces between frames
        """
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

            face_positions = []
            face_sizes = []
            frames_with_faces = 0

            for frame in frames[:10]:  # Check up to 10 frames
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))

                if len(faces) > 0:
                    frames_with_faces += 1
                    # Track the largest face
                    largest = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = largest
                    face_positions.append((x + w//2, y + h//2))  # Center
                    face_sizes.append(w * h)

            total_checked = min(len(frames), 10)

            # If faces appear/disappear inconsistently
            if frames_with_faces > 0 and frames_with_faces < total_checked * 0.7:
                if total_checked > 3:
                    details.append(AnalysisDetail(
                        category="Deepfake Detection",
                        finding=f"Face detection inconsistent: face found in {frames_with_faces}/{total_checked} frames — face may be swapped or unstable",
                        confidence=0.55,
                        severity=RiskLevel.HIGH
                    ))

            # Check face position jitter
            if len(face_positions) >= 3:
                positions = np.array(face_positions, dtype=float)
                pos_diffs = np.sqrt(np.sum(np.diff(positions, axis=0)**2, axis=1))
                pos_std = np.std(pos_diffs)
                pos_mean = np.mean(pos_diffs)

                # High jitter relative to movement = face swap artifacts
                if pos_mean > 0 and pos_std / pos_mean > 1.5:
                    details.append(AnalysisDetail(
                        category="Deepfake Detection",
                        finding=f"Face position shows erratic jitter across frames (CV={pos_std/pos_mean:.2f}) — common in face-swap deepfakes",
                        confidence=min(0.7, 0.3 + pos_std / pos_mean * 0.2),
                        severity=RiskLevel.HIGH
                    ))

            # Check face size consistency
            if len(face_sizes) >= 3:
                size_cv = np.std(face_sizes) / np.mean(face_sizes) if np.mean(face_sizes) > 0 else 0
                if size_cv > 0.5:
                    details.append(AnalysisDetail(
                        category="Deepfake Detection",
                        finding=f"Face size varies significantly across frames (CV={size_cv:.2f}) — may indicate face replacement",
                        confidence=min(0.6, 0.25 + size_cv * 0.4),
                        severity=RiskLevel.MEDIUM
                    ))

        except Exception as e:
            print(f"Face temporal analysis error: {e}")

    # ─── Compression Analysis ────────────────────────────────────────────
    def _check_compression(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Check for re-encoding indicators in container."""
        if fmt == "MP4":
            moov_count = data.count(b'moov')
            if moov_count > 1:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Multiple container headers detected ({moov_count}) — video has been re-encoded or concatenated",
                    confidence=0.6,
                    severity=RiskLevel.MEDIUM
                ))

            # Check for editing software signatures
            edit_tools = [
                b'ffmpeg', b'handbrake', b'premiere', b'after effects',
                b'davinci', b'final cut', b'camtasia', b'obs',
            ]
            data_lower = data[:50000].lower()
            for tool in edit_tools:
                if tool in data_lower:
                    details.append(AnalysisDetail(
                        category="Manipulation",
                        finding=f"Video editing software detected: {tool.decode()} — video has been processed",
                        confidence=0.45,
                        severity=RiskLevel.MEDIUM
                    ))
                    break

    # ─── Resolution Check ────────────────────────────────────────────────
    def _resolution_check(self, width: int, height: int, details: List[AnalysisDetail]):
        """Check for AI-typical resolutions."""
        ai_resolutions = [
            (512, 512), (768, 768), (1024, 1024),
            (512, 768), (768, 512),
            (576, 1024), (1024, 576),
        ]
        if (width, height) in ai_resolutions:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Video resolution ({width}x{height}) matches common AI video generation output sizes",
                confidence=0.4,
                severity=RiskLevel.MEDIUM
            ))

    # ─── Audio Track Check ───────────────────────────────────────────────
    def _audio_track_check(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Check if video has an audio track (AI videos often don't)."""
        if fmt == "MP4":
            # Look for audio track markers
            has_audio = b'mp4a' in data or b'aac' in data.lower() or b'soun' in data
            if not has_audio:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding="No audio track detected in video — AI-generated videos often lack audio",
                    confidence=0.45,
                    severity=RiskLevel.MEDIUM
                ))


video_analyzer = VideoAnalyzer()
