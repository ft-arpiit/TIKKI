from __future__ import annotations

import argparse
import logging
import re
import sys

from agent import TikkiAgent
from config import settings
from modules.tts import TextToSpeech


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def strip_wake_word(text: str) -> str:
    pattern = rf"^\s*{re.escape(settings.wake_word)}[\s,.:;-]*(.*)$"
    match = re.match(pattern, text, flags=re.I)
    return match.group(1).strip() if match else ""


def run_text(agent: TikkiAgent, tts: TextToSpeech, command: str) -> None:
    result = agent.run(command)
    print(f"TIKKI> {result}")
    tts.speak(result)


def run_voice(agent: TikkiAgent, tts: TextToSpeech) -> None:
    from modules.stt import SpeechToText

    stt = SpeechToText()
    print(f"Listening for '{settings.wake_word}'...")
    while True:
        try:
            heard = stt.listen_once()
            if not heard:
                continue

            if settings.require_wake_word:
                command = strip_wake_word(heard)
                if not command:
                    continue
            else:
                command = heard

            if command.lower() in {"quit", "exit", "shutdown tikki", "stop tikki"}:
                tts.speak("TIKKI shutting down.")
                break

            run_text(agent, tts, command)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            logging.getLogger(__name__).exception("Voice loop error")
            tts.speak("I hit an error and recovered. Please try again.")


def main() -> int:
    setup_logging()

    parser = argparse.ArgumentParser(description="PROJECT TIKKI")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="Run one command through TIKKI.")
    group.add_argument("--voice", action="store_true", help="Start hands-free voice mode.")
    args = parser.parse_args()

    agent = TikkiAgent()
    tts = TextToSpeech()

    if args.text:
        run_text(agent, tts, args.text)
        return 0

    if args.voice:
        run_voice(agent, tts)
        return 0

    print("PROJECT TIKKI")
    print("Use --text \"volume up\" or --voice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
