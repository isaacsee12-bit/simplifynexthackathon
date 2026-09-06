import hashlib
import struct
import io
import tempfile
import os
import wave
import numpy as np
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel

# Try loading librosa for real audio analysis
try:
    import librosa
    HAS_LIBROSA = True
    print("Librosa loaded successfully — advanced audio analysis enabled.")
except ImportError:
    HAS_LIBROSA = False
    print("Librosa not available — falling back to basic audio heuristics.")

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


class AudioAnalyzer:
    """
    Production-grade audio forensic analyzer for deepfake voice detection:
    1. MFCC-based spectral analysis (librosa)
    2. Pitch consistency and naturalness
    3. Spectral feature analysis (centroid, rolloff, bandwidth)
    4. Zero-crossing rate analysis
    5. Silence/pause pattern analysis
    6. Formant transition smoothness
    7. AI tool signature scanning
    8. WAV header and format analysis
    """

    def analyze(self, audio_bytes: bytes, filename: str = "") -> Tuple[List[AnalysisDetail], dict]:
        details = []
        file_size = len(audio_bytes)
        file_hash = hashlib.md5(audio_bytes[:4096]).hexdigest()

        fmt = self._detect_format(audio_bytes)

        # Try to load audio with librosa for real analysis
        audio_data = None
        sample_rate = None

        if HAS_LIBROSA:
            audio_data, sample_rate = self._load_audio(audio_bytes, fmt)

        if audio_data is not None and sample_rate is not None:
            # 1. MFCC-based spectral analysis
            self._mfcc_analysis(audio_data, sample_rate, details)

            # 2. Pitch analysis
            self._pitch_analysis(audio_data, sample_rate, details)

            # 3. Spectral feature analysis
            self._spectral_feature_analysis(audio_data, sample_rate, details)

            # 4. Zero-crossing rate analysis
            self._zero_crossing_analysis(audio_data, sample_rate, details)

            # 5. Silence/pause pattern analysis
            self._silence_analysis(audio_data, sample_rate, details)

            # 6. Temporal dynamics analysis
            self._temporal_dynamics_analysis(audio_data, sample_rate, details)
        else:
            # Fallback to byte-level heuristics
            self._byte_level_analysis(audio_bytes, fmt, details)

        # 7. AI tool signature scanning (always run)
        self._check_ai_signatures(audio_bytes, details)

        # 8. Format-specific checks (always run)
        self._format_analysis(audio_bytes, fmt, details)

        extra_context = {
            "file_size": file_size,
            "format": fmt,
            "file_hash": file_hash,
            "sample_rate": sample_rate or 0,
            "duration_seconds": round(len(audio_data) / sample_rate, 2) if audio_data is not None and sample_rate else 0,
            "librosa_available": HAS_LIBROSA,
        }

        # Reuse the decoded, mono 22050 Hz, at-most-60-second local sample.
        extra_context["media_audio"] = None
        if audio_data is not None and sample_rate:
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes((np.clip(audio_data, -1, 1) * 32767).astype("<i2").tobytes())
            extra_context["media_audio"] = output.getvalue()

        return details, extra_context

    def _detect_format(self, data: bytes) -> str:
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

    def _load_audio(self, audio_bytes: bytes, fmt: str):
        """Load audio bytes into numpy array using librosa."""
        tmp_path = None
        try:
            # Write to temp file since librosa works with file paths
            suffix_map = {
                "WAV": ".wav", "MP3": ".mp3", "FLAC": ".flac",
                "OGG": ".ogg", "M4A": ".m4a", "UNKNOWN": ".wav"
            }
            suffix = suffix_map.get(fmt, ".wav")

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            # Load with librosa (mono, resampled to 22050 by default)
            audio_data, sr = librosa.load(tmp_path, sr=22050, mono=True, duration=60)  # Cap at 60s
            os.remove(tmp_path)

            if len(audio_data) < 1000:
                return None, None

            return audio_data, sr
        except Exception as e:
            print(f"Audio loading error: {e}")
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return None, None

    # ─── MFCC Analysis ───────────────────────────────────────────────────
    def _mfcc_analysis(self, audio: np.ndarray, sr: int, details: List[AnalysisDetail]):
        """
        Analyze MFCC (Mel-Frequency Cepstral Coefficients).
        TTS/voice cloning produces MFCCs with different statistical properties:
        - Lower variance across time (too consistent)
        - Different distribution patterns
        """
        try:
            mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=20)

            # Compute statistics across time frames
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)
            mfcc_var = np.var(mfccs, axis=1)

            # Overall variability metric
            avg_std = np.mean(mfcc_std[1:])  # Skip first MFCC (energy)
            avg_var = np.mean(mfcc_var[1:])

            # TTS voices tend to have lower MFCC variance (too smooth/consistent)
            if avg_std < 8.0:
                confidence = min(0.8, 0.4 + (8.0 - avg_std) / 10.0)
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"MFCC analysis: unusually low spectral variation (σ={avg_std:.1f}) — synthetic voices are often too consistent",
                    confidence=round(confidence, 2),
                    severity=RiskLevel.HIGH
                ))
            elif avg_std < 12.0:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"MFCC analysis: moderately low spectral variation (σ={avg_std:.1f}) — may indicate processed or synthetic audio",
                    confidence=0.4,
                    severity=RiskLevel.MEDIUM
                ))

            # Check MFCC delta (rate of change) — TTS often lacks natural variation in deltas
            mfcc_delta = librosa.feature.delta(mfccs)
            delta_std = np.mean(np.std(mfcc_delta, axis=1))

            if delta_std < 3.0:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"MFCC delta analysis: very low rate of spectral change (Δσ={delta_std:.1f}) — typical of TTS/voice cloning output",
                    confidence=min(0.75, 0.35 + (3.0 - delta_std) / 5.0),
                    severity=RiskLevel.HIGH
                ))

        except Exception as e:
            print(f"MFCC analysis error: {e}")

    # ─── Pitch Analysis ──────────────────────────────────────────────────
    def _pitch_analysis(self, audio: np.ndarray, sr: int, details: List[AnalysisDetail]):
        """
        Analyze pitch (F0) patterns.
        Real speech has natural pitch variation; TTS is often too smooth or periodic.
        """
        try:
            # Extract pitch using piptrack
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)

            # Get the most prominent pitch per frame
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 50 and pitch < 800:  # Valid speech range
                    pitch_values.append(pitch)

            if len(pitch_values) < 20:
                return

            pitch_arr = np.array(pitch_values)
            pitch_mean = np.mean(pitch_arr)
            pitch_std = np.std(pitch_arr)
            pitch_range = np.max(pitch_arr) - np.min(pitch_arr)

            # Coefficient of variation for pitch
            pitch_cv = pitch_std / pitch_mean if pitch_mean > 0 else 0

            # Very low pitch variation = likely TTS
            if pitch_cv < 0.05:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"Pitch analysis: extremely stable pitch (CV={pitch_cv:.3f}) — natural speech has more variation",
                    confidence=min(0.8, 0.5 + (0.05 - pitch_cv) * 10),
                    severity=RiskLevel.HIGH
                ))
            elif pitch_cv < 0.1:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"Pitch analysis: unusually stable pitch (CV={pitch_cv:.3f}) — may indicate synthetic speech",
                    confidence=0.45,
                    severity=RiskLevel.MEDIUM
                ))

            # Check for pitch jumps (splicing indicators)
            pitch_diffs = np.abs(np.diff(pitch_arr))
            large_jumps = np.sum(pitch_diffs > pitch_std * 3)
            jump_ratio = large_jumps / len(pitch_diffs) if len(pitch_diffs) > 0 else 0

            if jump_ratio > 0.1:
                details.append(AnalysisDetail(
                    category="Manipulation",
                    finding=f"Pitch analysis: frequent large pitch jumps detected ({large_jumps} occurrences) — possible audio splicing",
                    confidence=min(0.7, 0.3 + jump_ratio * 3),
                    severity=RiskLevel.HIGH
                ))

        except Exception as e:
            print(f"Pitch analysis error: {e}")

    # ─── Spectral Feature Analysis ───────────────────────────────────────
    def _spectral_feature_analysis(self, audio: np.ndarray, sr: int, details: List[AnalysisDetail]):
        """
        Analyze spectral centroid, rolloff, and bandwidth.
        Synthetic voices often have different spectral characteristics.
        """
        try:
            # Spectral centroid — "center of mass" of the spectrum
            centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            centroid_std = np.std(centroid)
            centroid_mean = np.mean(centroid)

            # Spectral rolloff — frequency below which 85% of energy is concentrated
            rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
            rolloff_std = np.std(rolloff)

            # Spectral bandwidth
            bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]
            bandwidth_std = np.std(bandwidth)
            bandwidth_mean = np.mean(bandwidth)

            # TTS often has narrower and more consistent spectral bandwidth
            if bandwidth_mean > 0:
                bw_cv = bandwidth_std / bandwidth_mean
                if bw_cv < 0.15:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Spectral bandwidth unusually consistent (CV={bw_cv:.3f}) — synthetic voices often lack natural spectral variation",
                        confidence=min(0.7, 0.35 + (0.15 - bw_cv) * 5),
                        severity=RiskLevel.HIGH
                    ))

            # Low spectral centroid variation = monotone/synthetic
            if centroid_mean > 0:
                centroid_cv = centroid_std / centroid_mean
                if centroid_cv < 0.15:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Spectral centroid very stable (CV={centroid_cv:.3f}) — indicates flat, synthetic-like frequency content",
                        confidence=0.45,
                        severity=RiskLevel.MEDIUM
                    ))

        except Exception as e:
            print(f"Spectral analysis error: {e}")

    # ─── Zero-Crossing Rate Analysis ─────────────────────────────────────
    def _zero_crossing_analysis(self, audio: np.ndarray, sr: int, details: List[AnalysisDetail]):
        """
        Zero-crossing rate analysis.
        TTS voices tend to have more uniform ZCR patterns.
        """
        try:
            zcr = librosa.feature.zero_crossing_rate(audio)[0]
            zcr_std = np.std(zcr)
            zcr_mean = np.mean(zcr)

            if zcr_mean > 0:
                zcr_cv = zcr_std / zcr_mean
                if zcr_cv < 0.3:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Zero-crossing rate unusually uniform (CV={zcr_cv:.3f}) — synthetic audio often lacks natural dynamics",
                        confidence=min(0.55, 0.25 + (0.3 - zcr_cv)),
                        severity=RiskLevel.MEDIUM
                    ))

        except Exception as e:
            print(f"ZCR analysis error: {e}")

    # ─── Silence & Pause Analysis ────────────────────────────────────────
    def _silence_analysis(self, audio: np.ndarray, sr: int, details: List[AnalysisDetail]):
        """
        Analyze silence/pause patterns.
        TTS has unnaturally even pauses; real speech has variable pauses.
        """
        try:
            # Compute RMS energy
            rms = librosa.feature.rms(y=audio)[0]

            # Detect silent frames (RMS below threshold)
            silence_threshold = np.mean(rms) * 0.1
            is_silent = rms < silence_threshold

            # Find silence segments
            silence_lengths = []
            current_length = 0
            for s in is_silent:
                if s:
                    current_length += 1
                else:
                    if current_length > 0:
                        silence_lengths.append(current_length)
                    current_length = 0

            if len(silence_lengths) >= 3:
                silence_arr = np.array(silence_lengths)
                silence_cv = np.std(silence_arr) / np.mean(silence_arr) if np.mean(silence_arr) > 0 else 0

                # TTS pauses are very uniform
                if silence_cv < 0.2 and len(silence_lengths) > 5:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Pause pattern analysis: silences are unnaturally uniform (CV={silence_cv:.3f}, {len(silence_lengths)} pauses) — typical of TTS",
                        confidence=min(0.65, 0.3 + (0.2 - silence_cv) * 3),
                        severity=RiskLevel.HIGH
                    ))
                elif silence_cv < 0.4 and len(silence_lengths) > 5:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Pause pattern analysis: pauses are moderately uniform (CV={silence_cv:.3f}) — may indicate synthetic speech",
                        confidence=0.35,
                        severity=RiskLevel.MEDIUM
                    ))

        except Exception as e:
            print(f"Silence analysis error: {e}")

    # ─── Temporal Dynamics ───────────────────────────────────────────────
    def _temporal_dynamics_analysis(self, audio: np.ndarray, sr: int, details: List[AnalysisDetail]):
        """
        Analyze temporal dynamics (energy envelope).
        TTS often has different energy attack/decay patterns.
        """
        try:
            # RMS energy over time
            rms = librosa.feature.rms(y=audio)[0]

            if len(rms) < 20:
                return

            # Compute energy dynamics
            rms_diff = np.diff(rms)
            attack_smoothness = np.std(rms_diff)
            rms_mean = np.mean(rms)

            if rms_mean > 0:
                dynamics_cv = attack_smoothness / rms_mean

                # Very smooth energy transitions = possibly synthetic
                if dynamics_cv < 0.15:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Energy dynamics: very smooth temporal transitions (CV={dynamics_cv:.3f}) — natural speech has more abrupt energy changes",
                        confidence=0.4,
                        severity=RiskLevel.MEDIUM
                    ))

        except Exception as e:
            print(f"Temporal dynamics error: {e}")

    # ─── Byte-Level Fallback ─────────────────────────────────────────────
    def _byte_level_analysis(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Fallback analysis when librosa is not available."""
        audio_start = min(1000, len(data) // 4)
        audio_data = data[audio_start:audio_start + 20000]

        if len(audio_data) < 500:
            return

        # Check byte transition smoothness
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

        # Check for splicing (silence blocks)
        self._check_splicing_bytes(data, details)

    def _check_splicing_bytes(self, data: bytes, details: List[AnalysisDetail]):
        """Check for audio splicing via silence blocks in byte data."""
        audio_start = min(2000, len(data) // 4)
        sample = data[audio_start:audio_start + 30000]
        if len(sample) < 1000:
            return

        silence_blocks = 0
        current_silence = 0
        for b in sample:
            if b == 0 or b == 128:
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

    # ─── AI Tool Signature Scanning ──────────────────────────────────────
    def _check_ai_signatures(self, data: bytes, details: List[AnalysisDetail]):
        """Check for AI voice synthesis tool signatures in metadata."""
        ai_tools = [
            b'elevenlabs', b'resemble', b'coqui', b'tortoise-tts',
            b'bark', b'valle', b'xtts', b'mozilla-tts',
            b'tacotron', b'wavenet', b'vits', b'piper',
            b'espeak', b'festival', b'mary-tts', b'amazon polly',
            b'google cloud text-to-speech', b'azure speech',
            b'murf.ai', b'play.ht', b'speechify', b'listnr',
            b'uberduck', b'fakeyou', b'voicemod',
        ]
        data_lower = data[:30000].lower()
        for tool in ai_tools:
            if tool in data_lower:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"AI voice synthesis tool signature found: {tool.decode()}",
                    confidence=0.95,
                    severity=RiskLevel.CRITICAL
                ))
                break

    # ─── Format-Specific Analysis ────────────────────────────────────────
    def _format_analysis(self, data: bytes, fmt: str, details: List[AnalysisDetail]):
        """Format-specific header analysis."""
        if fmt == "WAV" and len(data) >= 44:
            try:
                channels = struct.unpack('<H', data[22:24])[0]
                sample_rate = struct.unpack('<I', data[24:28])[0]
                bits_per_sample = struct.unpack('<H', data[34:36])[0]

                standard_rates = [8000, 16000, 22050, 44100, 48000, 96000]
                if sample_rate not in standard_rates:
                    details.append(AnalysisDetail(
                        category="Manipulation",
                        finding=f"Non-standard sample rate ({sample_rate}Hz) — audio may have been resampled or processed",
                        confidence=0.5,
                        severity=RiskLevel.MEDIUM
                    ))

                # Common TTS output: 16kHz or 22.05kHz, 16-bit mono
                if sample_rate <= 22050 and bits_per_sample <= 16 and channels == 1:
                    details.append(AnalysisDetail(
                        category="AI Generation",
                        finding=f"Audio profile ({sample_rate}Hz, {bits_per_sample}-bit, mono) matches typical TTS output format",
                        confidence=0.35,
                        severity=RiskLevel.MEDIUM
                    ))
            except (struct.error, IndexError):
                pass


audio_analyzer = AudioAnalyzer()
