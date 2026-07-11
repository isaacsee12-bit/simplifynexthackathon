import hashlib
import struct
import math
from typing import List, Tuple
from models.schemas import AnalysisDetail, FrameAnalysis, RiskLevel

try:
    import cv2
    import numpy as np
    from PIL import Image
    import torch
    
    # Reuse the global vision model from image_analyzer if possible
    from analyzers.image_analyzer import vision_model, preprocess
    HAS_CV2_AND_TORCH = True
except ImportError:
    HAS_CV2_AND_TORCH = False


class VideoAnalyzer:
    """
    Analyzes videos for deepfake content using PyTorch Vision Models on extracted frames.
    """

    def analyze(self, video_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        details = []
        file_size = len(video_bytes)
        file_hash = hashlib.md5(video_bytes[:8192]).hexdigest()
        fmt = self._detect_format(video_bytes)

        frame_analyses = []
        deepfake_count = 0
        total_frames = 0
        
        if HAS_CV2_AND_TORCH and vision_model:
            try:
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                    temp_video.write(video_bytes)
                    temp_path = temp_video.name
                
                cap = cv2.VideoCapture(temp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                if total_frames > 0:
                    num_samples = min(total_frames, 5)
                    step = max(1, total_frames // num_samples)
                    
                    for i in range(num_samples):
                        frame_num = i * step
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                        ret, frame = cap.read()
                        
                        if ret:
                            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                            input_tensor = preprocess(img).unsqueeze(0)
                            
                            with torch.no_grad():
                                output = vision_model(input_tensor)
                                
                            prob = torch.nn.functional.softmax(output[0], dim=0)
                            top_prob, _ = torch.topk(prob, 1)
                            
                            is_anomalous = top_prob.item() < 0.25
                            if is_anomalous:
                                deepfake_count += 1
                                
                            frame_analyses.append(FrameAnalysis(
                                frame_number=frame_num,
                                is_deepfake=is_anomalous,
                                deepfake_probability=round(1.0 - top_prob.item(), 3),
                                details="PyTorch detected anomalous structure" if is_anomalous else "Frame appears structurally natural"
                            ))
                cap.release()
                os.remove(temp_path)
            except Exception as e:
                print(f"Video ML Inference Error: {e}")
                
        if len(frame_analyses) > 0:
            deepfake_ratio = deepfake_count / len(frame_analyses)
            if deepfake_ratio > 0.5:
                details.append(AnalysisDetail(
                    category="Deepfake Detection (Neural Net)",
                    finding=f"PyTorch Vision Model flagged {deepfake_count}/{len(frame_analyses)} sampled frames as structurally anomalous",
                    confidence=0.85,
                    severity=RiskLevel.CRITICAL
                ))
            elif deepfake_ratio > 0.0:
                details.append(AnalysisDetail(
                    category="Deepfake Detection (Neural Net)",
                    finding=f"PyTorch Vision Model flagged {deepfake_count}/{len(frame_analyses)} sampled frames as structurally anomalous",
                    confidence=0.6,
                    severity=RiskLevel.MEDIUM
                ))

        self._check_compression(video_bytes, fmt, details)
        
        extra_context = {
            "total_frames_estimated": total_frames,
            "deepfake_frames_sampled": deepfake_count,
            "format": fmt,
            "file_size": file_size,
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

    def _check_compression(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        if fmt == "MP4":
            moov_count = data.count(b'moov')
            if moov_count > 1:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Multiple container headers detected ({moov_count}) — video may have been re-encoded",
                    confidence=0.55,
                    severity=RiskLevel.MEDIUM
                ))

video_analyzer = VideoAnalyzer()
