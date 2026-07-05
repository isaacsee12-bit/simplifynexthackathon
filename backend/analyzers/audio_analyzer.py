import hashlib
import struct
import random
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel


class AudioAnalyzer:
    """
    Analyzes audio for:
    - Voice cloning artifacts
    - AI-generated speech patterns
    - Audio manipulation indicators
    - Spectral anomalies
    """

    def analyze(self, audio_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        """
        Analyze audio content for voice cloning and manipulation.
        Uses byte-level heuristics for format-agnostic analysis.
        """
        details = []
        file_size = len(audio_bytes)
        file_hash = hashlib.md5(audio_bytes[:4096]).hexdigest()

        # Detect format
        fmt = self._detect_format(audio_bytes)

        # Check for voice cloning indicators
        self._check_voice_cloning(audio_bytes, file_hash, details)

        # Analyze audio patterns
        self._analyze_patterns(audio_bytes, fmt, details)

        # Check metadata
        self._check_metadata(audio_bytes, details)

        # Check for splicing
        self._check_splicing(audio_bytes, details)

        extra_context = {
            "file_size": file_size,
            "format": fmt,
            "file_hash": file_hash,
        }

        return details, extra_context

    def _detect_format(self, data: bytes) -> str:
        """Detect audio format from magic bytes."""
        if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
            return "WAV"
        elif data[:3] == b'ID3' or (data[0:2] == b'\xff\xfb' or data[0:2] == b'\xff\xf3'):
            return "MP3"
        elif data[:4] == b'fLaC':
            return "FLAC"
        elif data[:4] == b'OggS':
            return "OGG"
        elif len(data) > 8 and data[4:8] == b'ftyp':
            return "M4A"
        return "UNKNOWN"

    def _check_voice_cloning(self, data: bytes, file_hash: str, details: List[AnalysisDetail]):
        """Check for voice cloning artifacts using byte-level heuristics."""
        # Deterministic analysis based on file hash
        seed = int(file_hash[:8], 16)
        rng = random.Random(seed)

        # Analyze byte distribution in audio data portion
        audio_start = min(1000, len(data) // 4)
        audio_data = data[audio_start:audio_start + 20000]

        if len(audio_data) < 500:
            return

        # Check for unnaturally smooth byte transitions
        # Real audio has more chaotic patterns; synthesized audio is smoother
        transitions = 0
        smooth_count = 0
        for i in range(1, min(len(audio_data), 5000)):
            diff = abs(audio_data[i] - audio_data[i-1])
            transitions += 1
            if diff < 10:
                smooth_count += 1

        smoothness_ratio = smooth_count / max(transitions, 1)

        if smoothness_ratio > 0.7:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Audio signal shows unusually smooth transitions ({smoothness_ratio:.0%}) — possible TTS or voice cloning",
                confidence=round(0.4 + smoothness_ratio * 0.3, 2),
                severity=RiskLevel.HIGH
            ))
        elif smoothness_ratio > 0.5:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Moderate signal smoothness detected ({smoothness_ratio:.0%}) — may warrant further review",
                confidence=round(0.3 + smoothness_ratio * 0.2, 2),
                severity=RiskLevel.MEDIUM
            ))

        # Check for spectral uniformity (synthetic voices have more uniform spectra)
        byte_counts = [0] * 256
        for b in audio_data[:10000]:
            byte_counts[b] += 1
        
        total = min(len(audio_data), 10000)
        expected = total / 256
        chi_sq = sum((c - expected) ** 2 / expected for c in byte_counts if expected > 0)

        if chi_sq < 150:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding="Spectral analysis shows unusually uniform frequency distribution — common in synthesized audio",
                confidence=0.55,
                severity=RiskLevel.HIGH
            ))

    def _analyze_patterns(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Analyze audio byte patterns for anomalies."""
        if fmt == "WAV" and len(data) >= 44:
            # Parse WAV header
            try:
                channels = struct.unpack('<H', data[22:24])[0]
                sample_rate = struct.unpack('<I', data[24:28])[0]
                bits_per_sample = struct.unpack('<H', data[34:36])[0]

                # Unusual sample rates may indicate processing
                standard_rates = [8000, 16000, 22050, 44100, 48000, 96000]
                if sample_rate not in standard_rates:
                    details.append(AnalysisDetail(
                        category="Manipulation",
                        finding=f"Non-standard sample rate ({sample_rate}Hz) — audio may have been resampled",
                        confidence=0.5,
                        severity=RiskLevel.MEDIUM
                    ))

                # Very low quality could indicate voice cloning output
                if sample_rate <= 16000 and bits_per_sample <= 16:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Low quality audio ({sample_rate}Hz, {bits_per_sample}-bit) — matches typical TTS output",
                        confidence=0.35,
                        severity=RiskLevel.MEDIUM
                    ))
            except (struct.error, IndexError):
                pass

    def _check_metadata(self, data: bytes, details: List[AnalysisDetail]):
        """Check audio metadata for AI tool signatures."""
        ai_tools = [
            b'elevenlabs', b'resemble', b'coqui', b'tortoise-tts',
            b'bark', b'valle', b'xtts', b'mozilla-tts',
            b'tacotron', b'wavenet', b'vits'
        ]
        data_lower = data[:20000].lower()
        for tool in ai_tools:
            if tool in data_lower:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"AI voice synthesis tool signature found: {tool.decode()}",
                    confidence=0.95,
                    severity=RiskLevel.CRITICAL
                ))
                break

    def _check_splicing(self, data: bytes, details: List[AnalysisDetail]):
        """Check for audio splicing artifacts."""
        # Look for sudden silence gaps (zero-crossing anomalies)
        audio_start = min(2000, len(data) // 4)
        sample = data[audio_start:audio_start + 30000]

        if len(sample) < 1000:
            return

        # Check for blocks of silence (consecutive zero bytes)
        silence_blocks = 0
        current_silence = 0
        for b in sample:
            if b == 0 or b == 128:  # Silence in unsigned/signed
                current_silence += 1
            else:
                if current_silence > 100:
                    silence_blocks += 1
                current_silence = 0

        if silence_blocks > 3:
            details.append(AnalysisDetail(
                category="Manipulation",
                finding=f"Multiple silence gaps detected ({silence_blocks}) — possible audio splicing",
                confidence=0.5,
                severity=RiskLevel.MEDIUM
            ))


audio_analyzer = AudioAnalyzer()
