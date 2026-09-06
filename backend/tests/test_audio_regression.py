"""Real-signal coverage for the non-JIT pitch path and sampled audio payload."""

import io
from pathlib import Path
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyzers.audio_analyzer import AudioAnalyzer, librosa


class AudioRegressionTests(unittest.TestCase):
    rate = 22050

    def test_worker_analysis_preserves_real_audio_and_heuristics(self):
        samples = (np.sin(2 * np.pi * 440 * np.arange(self.rate * 2) / self.rate)
                   * 12000).astype("<i2")
        source = io.BytesIO()
        with wave.open(source, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.rate)
            wav.writeframes(samples.tobytes())
        with patch.object(librosa, "piptrack", side_effect=AssertionError("Unsafe JIT path")) as piptrack:
            with ThreadPoolExecutor(max_workers=1) as executor:
                for _ in range(2):
                    details, context = executor.submit(
                        AudioAnalyzer().analyze, source.getvalue(), "sine.wav"
                    ).result(timeout=30)
                    findings = [detail.finding for detail in details]
                    self.assertTrue(any("extremely stable pitch" in f for f in findings))
                    self.assertTrue(any("MFCC analysis" in f for f in findings))
                    self.assertTrue(any("Spectral centroid" in f for f in findings))
                    self.assertEqual(context["sample_rate"], self.rate)
                    self.assertEqual(context["duration_seconds"], 2)
                    with wave.open(io.BytesIO(context["media_audio"]), "rb") as wav:
                        self.assertEqual(wav.getnchannels(), 1)
                        self.assertEqual(wav.getsampwidth(), 2)
                        self.assertEqual(wav.getframerate(), self.rate)
                        self.assertEqual(wav.getnframes(), len(samples))
                        decoded = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
                    np.testing.assert_allclose(decoded, samples, atol=1, rtol=0)
            piptrack.assert_not_called()

    def test_pitch_distinguishes_stable_varying_and_unvoiced_signals(self):
        time = np.arange(self.rate * 2) / self.rate
        signals = {
            "stable": 0.4 * np.sin(2 * np.pi * 440 * time),
            "varying": 0.4 * np.sin(2 * np.pi * (200 * time + 100 * time ** 2)),
            "silence": np.zeros_like(time),
            "outside_speech_range": 0.4 * np.sin(2 * np.pi * 1200 * time),
            "short": 0.4 * np.sin(2 * np.pi * 440 * time[:2205]),
        }
        for name, audio in signals.items():
            with self.subTest(signal=name):
                details = []
                AudioAnalyzer()._pitch_analysis(audio.astype(np.float32), self.rate, details)
                stable = any("stable pitch" in detail.finding for detail in details)
                self.assertEqual(stable, name == "stable")
                if name in ("silence", "outside_speech_range", "short"):
                    self.assertEqual(details, [])


if __name__ == "__main__":
    unittest.main()
