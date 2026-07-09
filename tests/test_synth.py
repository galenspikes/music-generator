"""The in-process MIDI→WAV synthesizer (synth.py) and its web endpoint.

The contract: any MIDI the engine produces renders to a valid, non-silent,
deterministic WAV — with no FluidSynth binary and no SoundFont anywhere in
the loop.
"""
import io
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

import generator_api as api
import synth
from webapp.backend.app import app

client = TestClient(app)


def _wav_info(data: bytes):
    with wave.open(io.BytesIO(data), "rb") as w:
        frames = w.readframes(w.getnframes())
        return w.getframerate(), w.getnchannels(), w.getsampwidth(), frames


@pytest.fixture(scope="module")
def flat_result():
    return api.generate({"keys": "C::maj7, A::min9", "seconds": 3, "seed": 5,
                         "perc_main": "qb, eg, qc, eg"})


class TestRenderWav:
    def test_valid_wav_structure(self, flat_result):
        data = synth.render_wav(flat_result.midi)
        assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
        rate, channels, width, frames = _wav_info(data)
        assert rate == synth.DEFAULT_SAMPLE_RATE
        assert channels == 1
        assert width == 2  # 16-bit PCM
        assert len(frames) > 0

    def test_duration_matches_piece(self, flat_result):
        rate, _c, _w, frames = _wav_info(synth.render_wav(flat_result.midi))
        seconds = (len(frames) // 2) / rate
        # piece length plus up to the fixed tail allowance
        assert flat_result.duration_seconds <= seconds \
            <= flat_result.duration_seconds + 2.0

    def test_not_silent_and_not_clipped(self, flat_result):
        samples = synth.synthesize(flat_result.midi)
        assert float(np.max(np.abs(samples))) > 0.05, "audible signal expected"
        assert float(np.max(np.abs(samples))) <= 1.0

    def test_deterministic(self, flat_result):
        assert synth.render_wav(flat_result.midi) == \
            synth.render_wav(flat_result.midi)

    def test_drums_only_render(self):
        res = api.generate({"keys": "", "random_roots": True, "seconds": 2,
                            "seed": 1, "perc_main": "qb, eg, qc, ei",
                            "bass_style": "none"})
        samples = synth.synthesize(res.midi)
        assert float(np.max(np.abs(samples))) > 0.02

    def test_custom_sample_rate(self, flat_result):
        rate, _c, _w, _f = _wav_info(
            synth.render_wav(flat_result.midi, sample_rate=8000))
        assert rate == 8000

    def test_song_path_renders(self):
        res = api.generate({"song_yaml": (
            "title: t\ntempo: 130\nsections:\n"
            "  - name: a\n    repeat: 1\n    keys: 'C::maj7, G::7'\n"),
            "seed": 2})
        assert synth.render_wav(res.midi)[:4] == b"RIFF"


class TestAudioEndpoint:
    def test_returns_wav(self):
        r = client.post("/api/audio", json={"spec": {
            "keys": "C::maj7, F::maj7", "seconds": 2, "seed": 9}})
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        assert r.content[:4] == b"RIFF"

    def test_bad_spec_is_structured_422(self):
        r = client.post("/api/audio", json={"spec": {
            "keys": "ZZ", "seconds": 2}})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert detail["error_type"] == "invalid_chord"
        assert detail["code"] == "ERR_CHORD_001"
