# PROJECT TIKKI v1.0

Autonomous, local-first Windows OS co-pilot.

## Design goals

- Deterministic local routing for common Windows actions.
- No cloud call on the fast path.
- Local offline STT with faster-whisper.
- Local TTS with pyttsx3 by default.
- RAM-based screenshots with MSS.
- Optional multimodal visual grounding through Google Gemini.
- Strict action validation and bounded retries.
- LangGraph orchestration with a simple fallback path if LangGraph is unavailable.

> Latency and reliability are measured engineering targets, not mathematical guarantees. The local router avoids network/model calls; Windows APIs, process startup, drivers, and scheduling still introduce variable latency.

## Quick start

1. Install Python 3.11+.
2. Create and activate a virtual environment:
   `py -3.11 -m venv .venv`
   `.venv\Scripts\activate`
3. Install:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Put a Gemini API key in `GEMINI_API_KEY` only if visual grounding is desired.
6. Run:
   `python main.py --text "volume up"`
   or:
   `python main.py --voice`

## Optional CUDA

If the machine has an NVIDIA GPU, configure faster-whisper for CUDA according to the installed CUDA/cuDNN stack. Otherwise the default CPU INT8 configuration is used.

## Safety model

The model never gets a raw shell tool. Visual grounding can only emit bounded actions:
move, click, double_click, type, scroll, hotkey, wait.

For production deployment, keep sensitive applications outside automated workflows unless explicitly tested.
