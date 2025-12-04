# app/main.py — Phase 8 Gateway Integration

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json

# Używamy modułów z pakietu app.*
from app.gyroscope import MetaArchitectController
from app.memory import VectorMemory
from app.gyroscope_memory import MemorySynapse
from app.util import embed_intent

app = FastAPI()


# Prosty „ping” na root — żeby / nie zwracało 404
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Gyroscope Gateway online",
        "endpoints": ["/v1/chat/completions"],
        "headers": {
            "x-gyro-mode": "architect | (fallback: normal)",
            "x-gyro-memory": "none | read | write | rw",
        },
    }


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    body = await request.json()
    headers = request.headers

    gyro_mode = headers.get("x-gyro-mode", "").lower()
    memory_mode = headers.get("x-gyro-memory", "none").lower()

    stream = bool(body.get("stream", False))
    messages = body.get("messages", [])

    # Wyciągamy ostatni user prompt
    user_prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_prompt = msg.get("content", "")
            break

    # ===========================
    # NORMALNY TRYB (bez architect)
    # ===========================
    if gyro_mode != "architect":
        # Tu możesz później wstawić swoją starą logikę proxy do OpenAI
        # lub do innego kontrolera. Na razie jasno sygnalizujemy brak:
        raise NotImplementedError("Non-architect mode handling is not implemented yet.")

    # ===========================
    # ARCHITECT MODE + MEMORY
    # ===========================

    # 1) MEMORY READ (warm start)
    retrieved_engram = None
    seed_blueprint_text = None

    if memory_mode in ("read", "rw"):
        print(">>> GATEWAY: MEMORY READ ENABLED (architect)")
        intent_vec = embed_intent(user_prompt)
        retrieved_engram = VectorMemory.query_best(intent_vec)
        if retrieved_engram:
            sim = retrieved_engram.get("_similarity", 0.0)
            print(f">>> GATEWAY: Engram found (similarity={sim:.3f})")
            seed_blueprint_text = retrieved_engram.get("blueprint_final")

            # Jeśli chcesz kiedyś użyć fizyki z Engramu:
            control_params = retrieved_engram.get("control_parameters") or {}
            if control_params:
                # Przekażemy je później do MetaArchitectController, gdy dodamy wsparcie
                print(">>> GATEWAY: control_parameters available (not yet applied).")

    # 2) Przygotuj MetaArchitectController
    meta = MetaArchitectController(model_name="gpt-4.1-mini")

    # Jeśli mamy seed blueprint, wstrzykujemy go w prompt
    if seed_blueprint_text:
        augmented_prompt = (
            f"GOAL: {user_prompt}\n\n"
            "You previously solved a very similar problem with this high-level plan:\n"
            f"{seed_blueprint_text}\n\n"
            "Now create and refine an updated blueprint and final solution, "
            "reusing the structural pattern where it makes sense, but adapting "
            "it cleanly to this new GOAL.\n\n"
            "User-facing GOAL (for the final answer) is still:\n"
            f"{user_prompt}"
        )
        effective_prompt = augmented_prompt
    else:
        effective_prompt = user_prompt

    # 3) Strumień SSE: status + content + (opcjonalnie) zapis Engramu
    async def architect_event_stream():
        final_chunks: list[str] = []
        blueprint_snapshot: str = ""

        async for event in meta.process_meta(effective_prompt):
            if event["type"] == "status":
                payload = {"status": event["message"]}
                yield "event: status\n"
                yield f"data: {json.dumps(payload)}\n\n"

                # złap finalny blueprint (do pamięci)
                if event["message"].startswith("Final Blueprint:"):
                    blueprint_snapshot = event["message"].replace(
                        "Final Blueprint:", ""
                    ).strip()

            elif event["type"] == "content":
                chunk = event.get("chunk", "")
                final_chunks.append(chunk)

                data = {
                    "id": "gyro-architect-1",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": "gyroscope-v1-architect",
                    "choices": [
                        {
                            "delta": {"content": chunk},
                            "index": 0,
                            "finish_reason": None,
                        }
                    ],
                }

                yield "event: content\n"
                yield f"data: {json.dumps(data)}\n\n"

        # --- MEMORY WRITE ---
        if memory_mode in ("write", "rw"):
            print(">>> GATEWAY: MEMORY WRITE ENABLED (architect)")

            full_text = "".join(final_chunks).strip()

            # Na razie podstawowe telemetry „na sucho”
            fake_session_history = []
            fake_final_risk_profile = {
                "risk": 0.5,
                "entropy": 0.0,
                "variance": 0.0,
                "repetition_rate": 0.0,
                "temperature": 0.7,
            }

            control_params = MemorySynapse.extract_telemetry(
                fake_session_history,
                fake_final_risk_profile,
            )

            engram = {
                "intent_embedding": embed_intent(user_prompt),
                "structural_embedding": [],
                "code_embedding": [],
                "blueprint_final": blueprint_snapshot or "",
                "control_parameters": control_params,
                "metadata": {
                    "domain": "architect",
                    "prompt": user_prompt,
                },
            }

            VectorMemory.store(engram)
            print(">>> GATEWAY: Engram stored (architect).")

        # Koniec strumienia
        yield "event: done\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(architect_event_stream(), media_type="text/event-stream")