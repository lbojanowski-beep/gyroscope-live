# Gyroscope Live – Meta-Architect Gateway + Clean Architecture Snake

This repo contains two main components:

1. **Gyroscope Meta-Architect Gateway** – a FastAPI-based proxy that exposes a `/v1/chat/completions` endpoint compatible with the OpenAI API, extended with:
   - `x-gyro-mode: architect` – enables the Meta-Architect planning + execution loop,
   - `x-gyro-memory: read | write | rw` – enables vector-based memory for structural reuse (Engrams).

2. **Clean Architecture Snake Game** – a reference implementation of the Snake game in Python, using a layered, clean architecture:
   - Domain layer (pure game rules),
   - Use case layer,
   - Interface adapters,
   - Infrastructure adapters (Pygame).

---

## 1. Setup

```bash
git clone https://github.com/your-user/gyroscope_live.git
cd gyroscope_live

python -m venv venv
source venv/bin/activate  # on macOS/Linux

pip install -r requirements.txt  # or: pip install fastapi uvicorn openai pygame