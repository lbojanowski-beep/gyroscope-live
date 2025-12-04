import os
import time
from typing import Tuple

from openai import OpenAI


"""
gyroscope_navigator.py

INTENT-01: The Recursive Deepener
Level 4: Intent Modulation via Active Feedforward Control.

Author: Łukasz (Interference Intelligence Lab)
"""


# ========= LLM WRAPPER =========

class LiveLLM:
    """
    Minimal wrapper around OpenAI completions API (2.x client).

    Uses a completion-style model that exposes temperature and behaves
    deterministically enough for our steering experiments.
    """

    def __init__(
        self,
        model: str = "gpt-3.5-turbo-instruct",
        base_temperature: float = 0.7,
    ):
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

        self.client = OpenAI()
        self.model = model
        self.base_temperature = base_temperature

    def generate_pulse(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = 200,
    ) -> Tuple[str, list, list]:
        """
        Single non-streaming completion.

        Returns:
            text (str),
            tokens (list[str]) – if logprobs available,
            logprobs (list[dict]) – may be empty (not used here).
        """
        if temperature is None:
            temperature = self.base_temperature

        response = self.client.completions.create(
            model=self.model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=1.0,
            n=1,
            stream=False,
            logprobs=0,  # we don't need detailed telemetry here
        )

        choice = response.choices[0]
        text = choice.text or ""

        lp = choice.logprobs
        tokens = lp.tokens if lp and lp.tokens else []
        top_logprobs = lp.top_logprobs if lp and lp.top_logprobs else []

        return text, tokens, top_logprobs


# ========= NAVIGATOR (LEVEL 4) =========

class NavigatorGyroscope:
    """
    Level 4 Controller.

    Cel:
      - przeciwdziałać SEMANTYCZNEMU DRYFOWI (uśrednianiu i spłycaniu),
      - wstrzykiwać „wektory pogłębiające” pomiędzy kolejne bloki tekstu.

    Mechanizm:
      - po każdym wygenerowanym bloku tekstu pytamy model (w trybie meta):
        „Co teraz należy zrobić, żeby pójść głębiej / bardziej krytycznie?”,
      - otrzymaną instrukcję [DIRECTION: ...] dołączamy do kontekstu,
      - dopiero wtedy generujemy kolejny blok.
    """

    def __init__(self, llm: LiveLLM):
        self.model = llm

    def _generate_deepening_vector(self, recent_text: str, depth_level: int) -> str:
        """
        The Critic:
        Analizuje poprzedni blok i generuje instrukcję, która ma wymusić
        'głębszy' kolejny akapit.
        """

        strategies = [
            "identify a hidden contradiction or tension in the previous argument",
            "explore the second-order consequences of this idea",
            "present and then refute the most obvious counter-argument",
            "connect this concept to a fundamental law of physics, biology, or logic",
        ]

        strategy = strategies[depth_level % len(strategies)]

        meta_prompt = (
            "You are a critical editor helping a writer avoid shallow, generic text.\n\n"
            f"TEXT SEGMENT:\n\"...{recent_text[-600:]}\"\n\n"
            "CRITICAL OBJECTIVE:\n"
            "The NEXT paragraph must NOT summarize or repeat. It must instead "
            f"{strategy}.\n\n"
            "Write a single, concrete, imperative instruction to the writer "
            "that forces this deeper move.\n"
            "Format your entire answer exactly as:\n"
            "[DIRECTION: ...]\n"
        )

        vector_text, _, _ = self.model.generate_pulse(
            meta_prompt,
            temperature=0.7,
            max_tokens=60,
        )

        clean = vector_text.strip().replace('"', "")
        if not clean.startswith("["):
            clean = f"[DIRECTION: {clean}]"

        print(f"   >>> NAVIGATOR: Deepening Vector = {clean}")
        return f"\n\n{clean}\n\n"

    def run_deepening_session(self, initial_prompt: str, steps: int = 4):
        """
        INTENT-01: Recursive Deepener.

        - initial_prompt: pytanie / teza startowa,
        - steps: ile razy mamy „pogłębić” dalej (poza pierwszym blokiem).
        """

        print("--- INTENT-01: THE RECURSIVE DEEPENER ---\n")
        print(f"ROOT PROMPT:\n{initial_prompt}\n")

        current_text = initial_prompt.strip() + "\n\n"

        # === BLOK 1: standardowa odpowiedź bez wektora ===
        block, _, _ = self.model.generate_pulse(
            current_text,
            temperature=0.7,
            max_tokens=200,
        )
        current_text += block
        print("[BLOCK 1]\n", block.strip(), "\n", sep="")

        last_block = block

        # === Kolejne kroki pogłębiania ===
        for i in range(steps):
            print(f"\n--- STEP {i+2} (Deepening) ---")

            # 1. wylicz wektor pogłębiający (critique)
            deep_vec = self._generate_deepening_vector(last_block, depth_level=i)

            # 2. dodaj wektor do kontekstu
            context_with_vector = current_text + deep_vec

            # 3. wygeneruj kolejny blok, już sterowany
            block, _, _ = self.model.generate_pulse(
                context_with_vector,
                temperature=0.85,   # trochę wyżej, bo mamy silne sterowanie
                max_tokens=250,
            )

            # 4. zapisz do historii
            current_text += deep_vec + block
            last_block = block

            print("[BLOCK", i + 2, "]\n", block.strip(), "\n", sep="")
            time.sleep(0.7)

        print("\n--- SESSION COMPLETE ---\n")
        print("===== FULL TEXT (with directions) =====\n")
        print(current_text)


# ========= MAIN =========

if __name__ == "__main__":
    # Upewnij się, że masz:
    # export OPENAI_API_KEY="sk-..."
    root_prompt = (
        "Analyze the concept of 'Time' not as a physical dimension, "
        "but as a biological illusion."
    )

    llm = LiveLLM()
    navigator = NavigatorGyroscope(llm)
    navigator.run_deepening_session(root_prompt, steps=4)