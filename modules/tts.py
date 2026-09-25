from __future__ import annotations

import logging
import queue
import threading

import comtypes
import win32com.client

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Windows native SAPI5 text-to-speech."""

    def __init__(
        self,
        rate: int = 185,
        volume: float = 0.9,
        voice: str = "",
    ) -> None:
        self.rate = rate
        self.volume = volume
        self.voice = voice

        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(
            target=self._worker,
            name="tikki-tts",
            daemon=True,
        )
        self._thread.start()

    def _speak_one(self, text: str) -> None:
        speaker = None

        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")

            sapi_rate = max(-10, min(10, int((self.rate - 175) / 20)))
            speaker.Rate = sapi_rate
            speaker.Volume = max(0, min(100, int(self.volume * 100)))

            if self.voice:
                try:
                    for voice in speaker.GetVoices():
                        description = voice.GetDescription()
                        if self.voice.lower() in description.lower():
                            speaker.Voice = voice
                            break
                except Exception:
                    logger.warning("Could not apply requested voice.")

            speaker.Speak(text)

        finally:
            speaker = None

    def _worker(self) -> None:
        com_initialized = False

        try:
            comtypes.CoInitialize()
            com_initialized = True

            logger.info("SAPI5 TTS worker initialized.")

            while True:
                text = self._queue.get()

                try:
                    if text is None:
                        break

                    self._speak_one(str(text))

                except Exception:
                    logger.exception("TTS playback failed")

                finally:
                    self._queue.task_done()

        except Exception:
            logger.exception("Could not initialize TTS worker.")

        finally:
            if com_initialized:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass

    def speak(self, text: str) -> None:
        if text:
            self._queue.put(str(text))

    def stop(self) -> None:
        self._queue.put(None)