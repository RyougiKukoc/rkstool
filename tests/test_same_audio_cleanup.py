"""Real BestSource audio comparisons must release their input files immediately."""

import gc
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave


class SameAudioCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import numpy  # noqa: F401
            import vapoursynth as vs
        except ImportError as error:
            raise unittest.SkipTest(f"Audio dependencies unavailable: {error}")
        try:
            vs.core.bs.AudioSource
        except (AttributeError, vs.Error) as error:
            raise unittest.SkipTest(f"BestSource unavailable: {error}")

        from rkstool import muxer

        cls.muxer = muxer

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="rkstool-audio-cleanup-test-")).resolve()
        self.addCleanup(self._cleanup)

    def _check_temporary_path(self):
        self.assertEqual(self.root.parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.root.name.startswith("rkstool-audio-cleanup-test-"))
        self.assertFalse(self.root.is_symlink())

    def _cleanup(self):
        self._check_temporary_path()
        if self.root.exists():
            # Cleanup after a failed assertion may need to collect the old leak.
            # The actual regression assertion below never collects or sleeps.
            gc.collect()
            shutil.rmtree(self.root)

    def _wav(self, name, *, channels=2, rate=48000, samples=10000, changed_sample=None):
        path = self.root / f"{name}.wav"
        data = bytearray(struct.pack("<h", 100) * channels * samples)
        if changed_sample is not None:
            struct.pack_into("<h", data, changed_sample * channels * 2, 2000)
        with wave.open(os.fspath(path), "wb") as stream:
            stream.setnchannels(channels)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(data)
        return os.fspath(path)

    def _assert_removed_immediately(self):
        self._check_temporary_path()
        # On Windows this raises WinError 32 while any source still holds a file.
        shutil.rmtree(self.root)
        self.assertFalse(self.root.exists())

    def _compare(self, expected, **second_options):
        first = self._wav("first")
        second = self._wav("second", **second_options)
        self.assertIs(self.muxer.same_audio(first, second), expected)
        self._assert_removed_immediately()

    def test_identical_samples(self):
        self._compare(True)

    def test_same_input_path(self):
        path = self._wav("same")
        self.assertIs(self.muxer.same_audio(path, path), True)
        self._assert_removed_immediately()

    def test_different_first_sample(self):
        self._compare(False, changed_sample=0)

    def test_different_last_sample(self):
        self._compare(False, changed_sample=9999)

    def test_different_sample_rates(self):
        self._compare(False, rate=44100)

    def test_different_channel_counts(self):
        self._compare(False, channels=1)

    def test_different_sample_counts(self):
        self._compare(False, samples=9000)

    def test_second_source_open_failure(self):
        import vapoursynth as vs

        first = self._wav("first")
        invalid = self.root / "invalid.wav"
        invalid.write_bytes(b"This is not a WAV file.")
        with self.assertRaises(vs.Error):
            self.muxer.same_audio(first, os.fspath(invalid))
        self._assert_removed_immediately()

    def test_comparison_exception(self):
        first = self._wav("first")
        second = self._wav("second")
        with patch.object(self.muxer.np, "allclose", side_effect=RuntimeError("comparison failed")):
            with self.assertRaisesRegex(RuntimeError, "comparison failed"):
                self.muxer.same_audio(first, second)
        self._assert_removed_immediately()


if __name__ == "__main__":
    unittest.main(verbosity=2)
