
from __future__ import annotations

import argparse
import logging
import sys

from agent import TikkiAgent
from config import settings
from modules.tts import TextToSpeech


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(
            logging,
            settings.log_level.upper(),
            logging.INFO,
        ),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_text(
    agent: TikkiAgent,
    tts: TextToSpeech,
    command: str,
) -> None:
    """Execute a single text command and speak the result."""

    command = command.strip()

    if not command:
        return

    print(f"COMMAND> {command}")

    try:
        result = agent.run(command)

        print(f"TIKKI> {result}")

        if result:
            tts.speak(result)

    except Exception as exc:
        logger.exception("Command execution failed")
        print(f"TIKKI ERROR> {exc}")

        try:
            tts.speak("I couldn't complete that command.")
        except Exception:
            pass


def run_voice(
    agent: TikkiAgent,
    tts: TextToSpeech,
) -> None:
    """
    Continuous voice mode.

    Wake-word detection is intentionally disabled.
    Every non-empty STT result is treated as a TIKKI command.
    """

    from modules.stt import SpeechToText

    stt = SpeechToText()

    print()
    print("=" * 60)
    print("PROJECT TIKKI — VOICE MODE")
    print("Wake word: DISABLED")
    print()
    print("Speak commands directly.")
    print()
    print("Examples:")
    print("  open Chrome")
    print("  volume up")
    print("  brightness up")
    print("  click the address bar")
    print("  type google.com")
    print("  press enter")
    print("  search Google for OpenAI")
    print()
    print("Say 'quit' to stop.")
    print("=" * 60)
    print()

    while True:
        try:
            heard = stt.listen_once()

            if not heard:
                continue

            heard = heard.strip()

            if not heard:
                continue

            print(f"HEARD> {heard}")

            # Exit commands are handled directly.
            normalized = heard.lower().strip(" .,!?;:")

            if normalized in {
                "quit",
                "exit",
                "shutdown tikki",
                "stop tikki",
            }:
                print("TIKKI> Shutting down.")
                tts.speak("TIKKI shutting down.")
                break

            # No wake-word check.
            # Every recognized command goes directly to the agent.
            run_text(
                agent,
                tts,
                heard,
            )

        except KeyboardInterrupt:
            print()
            print("TIKKI> Voice mode stopped.")
            break

        except Exception as exc:
            logger.exception("Voice loop error")
            print(f"VOICE ERROR> {exc}")

            try:
                tts.speak(
                    "I hit an error and recovered. Please try again."
                )
            except Exception:
                pass


def main() -> int:
    setup_logging()

    parser = argparse.ArgumentParser(
        description="PROJECT TIKKI"
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--text",
        help="Run one command through TIKKI.",
    )

    group.add_argument(
        "--voice",
        action="store_true",
        help="Start hands-free voice mode.",
    )

    args = parser.parse_args()

    try:
        agent = TikkiAgent()
        tts = TextToSpeech()
    except Exception as exc:
        logger.exception("Failed to initialize TIKKI")
        print(f"TIKKI INITIALIZATION ERROR> {exc}")
        return 1

    if args.text:
        run_text(
            agent,
            tts,
            args.text,
        )
        return 0

    if args.voice:
        run_voice(
            agent,
            tts,
        )
        return 0

    print("PROJECT TIKKI")
    print()
    print("Text mode:")
    print('  .venv\\Scripts\\python.exe main.py --text "volume up"')
    print()
    print("Voice mode:")
    print("  .venv\\Scripts\\python.exe main.py --voice")

    return 0


if __name__ == "__main__":
    sys.exit(main())