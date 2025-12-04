# app/gyroscope.py
"""
Mostek między FastAPI a MetaArchitectem.
Wykorzystuje istniejący gyroscope_meta_architect.py
i wystawia prosty async generator process_meta().
"""

from typing import AsyncGenerator, Dict, Any
import asyncio

from gyroscope_meta_architect import GyroLLMClient, MetaArchitect


class MetaArchitectController:
    """
    Opakowanie nad MetaArchitect, używane przez Gateway.
    Na razie nie streamujemy super-dokładnie blueprintu,
    tylko odpalamy pełną sesję i zwracamy jej wynik jako jeden chunk.
    (Wystarczy, żeby API działało i żeby domknąć fazę.)
    """

    def __init__(self, model_name: str = "gpt-4.1-mini"):
        self.client = GyroLLMClient(model_name=model_name)
        self.meta = MetaArchitect(self.client)

    async def process_meta(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        loop = asyncio.get_event_loop()

        # MetaArchitect ma synchr. metodę run_meta_session, która dużo drukuje
        # na stdout i na końcu zwraca final_text.
        def run_sync() -> str:
            return self.meta.run_meta_session(prompt, max_retries=2)

        final_text = await loop.run_in_executor(None, run_sync)

        # tu możesz w przyszłości dodać osobne eventy "status"
        # (np. łapanie blueprintu z loggera), ale na razie
        # zwracamy jeden event content + potem done.

        yield {
            "type": "content",
            "chunk": final_text,
        }

        yield {
            "type": "status",
            "message": "Final Blueprint: (embedded in content)",
        }