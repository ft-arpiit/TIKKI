from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from config import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(self) -> None:
        self.model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            cpu_threads=settings.whisper_cpu_threads,
        )

    @staticmethod
    def _rms(samples: np.ndarray) -> float:
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(samples.astype(np.float32)))))

    def _record_until_silence(self) -> np.ndarray:
        chunk_frames = int(settings.sample_rate * settings.audio_chunk_seconds)
        max_chunks = int(settings.max_listen_seconds / settings.audio_chunk_seconds)
        silence_chunks = max(1, int(settings.silence_seconds / settings.audio_chunk_seconds))

        chunks: list[np.ndarray] = []
        started = False
        silent = 0

        with sd.InputStream(
            samplerate=settings.sample_rate,
            channels=settings.audio_channels,
            dtype="float32",
            blocksize=chunk_frames,
        ) as stream:
            for _ in range(max_chunks):
                data, _overflowed = stream.read(chunk_frames)
                mono = data[:, 0].copy()
                level = self._rms(mono)

                if not started:
                    if level >= settings.start_rms:
                        started = True
                        chunks.append(mono)
                else:
                    chunks.append(mono)
                    if level < settings.start_rms:
                        silent += 1
                    else:
                        silent = 0
                    if silent >= silence_chunks:
                        break

        if not chunks:
            return np.empty(0, dtype=np.float32)
        return np.concatenate(chunks)

    def _transcribe_array(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = Path(tmp.name)

        try:
            pcm = np.clip(audio, -1.0, 1.0)
            pcm16 = (pcm * 32767).astype(np.int16)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(settings.sample_rate)
                wav.writeframes(pcm16.tobytes())

            segments, _info = self.model.transcribe(
                str(path),
                beam_size=1,
                language=settings.whisper_language or None,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            path.unlink(missing_ok=True)

    def listen_once(self) -> str:
        logger.debug("Listening...")
        audio = self._record_until_silence()
        text = self._transcribe_array(audio)
        logger.info("STT: %s", text)
        return text
