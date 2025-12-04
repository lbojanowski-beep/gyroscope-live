"""
gyroscope_autopoietic.py

HC-LIVE-03: The Autopoietic Pivot
Level 3 Autonomy: Metacognitive, self-generated pivot out of fixation loops.

Author: Łukasz (Interference Intelligence Lab)
"""

import os
import time
import math
from collections import deque, Counter
from typing import List, Dict, Tuple, Optional

import numpy as np
from openai import OpenAI


# ============== LOW-LEVEL METRICS (PMON-LIKE) ==============

def spectral_entropy_from_toplogprobs(
    top_logprobs_seq: List[Dict[str, float]]
) -> float:
    """
    Average normalized spectral entropy over a sequence of top_logprobs dicts.

    Each element: {token: logprob}
    H_norm in [0, 1], where 0 = very certain, 1 = very uncertain.
    """
    entropies = []

    for step in top_logprobs_seq:
        if not step:
            continue

        logps = np.array(list(step.values()), dtype=float)
        logps = logps - np.max(logps)
        ps = np.exp(logps)
        ps = ps / ps.sum()

        H = -np.sum(ps * np.log(ps + 1e-12))
        K = len(ps)
        if K > 1:
            H_norm = H / math.log(K)
        else:
            H_norm = 0.0
        entropies.append(H_norm)

    if not entropies:
        return 0.0

    return float(np.mean(entropies))


def variance_from_toplogprobs(
    top_logprobs_seq: List[Dict[str, float]]
) -> float:
    """
    Rough "variance" measure: variance of max probability across steps.
    """
    max_probs = []

    for step in top_logprobs_seq:
        if not step:
            continue

        logps = np.array(list(step.values()), dtype=float)
        logps = logps - np.max(logps)
        ps = np.exp(logps)
        ps = ps / ps.sum()
        max_probs.append(float(np.max(ps)))

    if len(max_probs) < 2:
        return 0.0

    return float(np.var(max_probs))


def repetition_rate(tokens: List[str], n: int = 2) -> float:
    """
    Simple n-gram repetition rate in a token sequence:
    ratio of the most frequent n-gram count to total n-grams.

    0.0 = no repetition, 1.0 = single n-gram dominates completely.
    """
    if len(tokens) < n + 1:
        return 0.0

    ngrams = []
    for i in range(len(tokens) - n + 1):
        ngram = tuple(tokens[i : i + n])
        ngrams.append(ngram)

    if not ngrams:
        return 0.0

    counts = Counter(ngrams)
    _, most_common_count = counts.most_common(1)[0]
    return most_common_count / max(1, len(ngrams))


# ============== LIVE LLM WRAPPER ==============

class LiveLLM:
    """
    Thin wrapper around OpenAI completions API for pulse-based generation.
    """

    def __init__(self, model: str = "gpt-3.5-turbo-instruct"):
        self.client = OpenAI()
        self.model = model

    def generate_pulse(
        self,
        prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 80,
        logit_bias: Optional[Dict[str, float]] = None,
        logprobs: int = 5,
    ) -> Tuple[str, List[str], List[Dict[str, float]]]:
        """
        One "pulse" of generation with logprobs.

        Returns:
            text_chunk: str
            tokens: List[str]
            top_logprobs_seq: List[Dict[str, float]]
        """
        response = self.client.completions.create(
            model=self.model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=1.0,
            n=1,
            stream=False,
            logprobs=logprobs,
            logit_bias=logit_bias if logit_bias else None,
        )

        choice = response.choices[0]
        text_chunk = choice.text or ""

        lp = choice.logprobs
        if lp is None:
            return text_chunk, [], []

        tokens = lp.tokens or []
        top_logprobs_seq = lp.top_logprobs or []

        return text_chunk, tokens, top_logprobs_seq


# ============== AUTOPOIETIC GYROSCOPE ==============

class AutopoieticGyroscope:
    """
    Level 3 Autonomy:
    - Alpha: Temperature regulation (risk-based).
    - Beta: Inhibitory control (loop attractor suppression).
    - Delta: Autopoietic Pivot (self-generated transition).
    """

    def __init__(
        self,
        llm: LiveLLM,
        base_temperature: float = 0.8,
        target_risk: float = 0.25,
        kp: float = 0.8,
        fixation_thresh: float = 0.30,   # <-- OBNIŻONY próg fiksacji
        history_maxlen: int = 400,
    ):
        self.llm = llm

        # Control parameters
        self.temperature = base_temperature
        self.target_risk = target_risk
        self.kp = kp
        self.fixation_thresh = fixation_thresh

        # State
        self.history_tokens: deque[str] = deque(maxlen=history_maxlen)
        self.logit_bias: Dict[str, float] = {}
        self.next_context_injection: str = ""

    # ---------- METRICS & META ----------

    def _calculate_metrics(
        self,
        tokens: List[str],
        top_logprobs_seq: List[Dict[str, float]],
    ) -> Tuple[float, float, float]:
        """
        Compute:
            combined_risk, entropy, rep2

        - entropy: from top_logprobs
        - rep2: 2-gram repetition in this pulse
        - combined_risk: 0.3 * PMON_risk + 0.7 * rep2
        """
        H = spectral_entropy_from_toplogprobs(top_logprobs_seq)  # [0,1]
        V = variance_from_toplogprobs(top_logprobs_seq)          # ~[0,0.25]
        V_norm = min(V / 0.25, 1.0)

        pmon_risk = 0.7 * H + 0.3 * V_norm
        rep2 = repetition_rate(tokens, n=2)

        combined_risk = 0.3 * pmon_risk + 0.7 * rep2

        return combined_risk, H, rep2

    def _generate_dynamic_pivot(self, context_tokens: deque[str]) -> str:
        """
        Metacognitive step:
        - use the model to generate a short, self-healing pivot sentence,
        - based on the last ~40 tokens of the stuck context.
        """
        recent_text = "".join(list(context_tokens)[-40:])

        meta_prompt = (
            f"TEXT SEGMENT: '...{recent_text}'\n\n"
            "TASK: The text above is stuck in a repetitive loop (fixation). "
            "Write ONE short, clear transitional sentence (max 20 tokens) that "
            "smoothly pivots from this loop to a related but distinct topic "
            "(for example: consequences, repair procedures, diagnostics, or impact). "
            "Do NOT repeat the loop. Do NOT use quotes or brackets. "
            "Just output the sentence."
        )

        print("   >>> REFLECTING: Generating Autopoietic Vector...")

        pivot_text, _, _ = self.llm.generate_pulse(
            meta_prompt,
            temperature=0.7,
            max_tokens=25,
        )

        clean_pivot = pivot_text.strip().replace('"', "").replace("'", "")
        if "." in clean_pivot:
            clean_pivot = clean_pivot.split(".")[0] + "."

        pivot_vec = f" [INTERRUPTION: {clean_pivot}] "
        print(f"   >>> METACOGNITION: Pivot = '{clean_pivot}'")
        return pivot_vec

    def _actuate(
        self,
        risk: float,
        entropy: float,
        rep2: float,
        tokens: List[str],
    ):
        """
        - Alpha: PID on temperature (smooth, bounded).
        - Beta + Delta: only when we truly have a loop:
          rep2 high AND entropy bardzo niskie.
        """
        # === ACTUATOR ALPHA: Temperature control ===
        error = risk - self.target_risk
        delta = self.kp * error
        self.temperature -= delta
        self.temperature = max(0.3, min(1.2, self.temperature))
        print(f"   >>> ALPHA: New Temp = {self.temperature:.2f}")

        self.next_context_injection = ""

        # === ACTUATOR BETA + DELTA: loop break & pivot ===
        # warunek zaostrzony na niską entropię
        if rep2 > self.fixation_thresh and entropy < 0.1:
            if self.history_tokens:
                most_common_token, _ = Counter(self.history_tokens).most_common(1)[0]
                print(f"   >>> BETA: Fixation detected on token '{most_common_token}'")
                # w produkcji tutaj można dodać logit_bias dla ID tego tokena

            pivot_vec = self._generate_dynamic_pivot(self.history_tokens)
            print(f"   >>> DELTA: Injecting Pivot: '{pivot_vec.strip()}'")

            self.next_context_injection = pivot_vec

            self.temperature = 0.8
            print(f"   >>> DELTA: Temp reset to {self.temperature:.2f}")

    # ---------- MAIN SESSION LOOP ----------

    def run_session(
        self,
        prompt: str,
        pulses: int = 8,
        max_tokens_per_pulse: int = 80,
    ) -> str:
        """
        Run an autopoietic session starting from an initial prompt.

        Returns the full generated text.
        """
        print("--- HC-LIVE-03: AUTOPOIETIC MODE ---")
        current_text = prompt
        full_text = prompt

        for i in range(pulses):
            print(f"\n[PULSE {i+1}]")
            print(f"   Temp before: {self.temperature:.2f}")

            prompt_for_step = current_text
            if self.next_context_injection:
                prompt_for_step += self.next_context_injection
                current_text += self.next_context_injection
                full_text += self.next_context_injection
                self.next_context_injection = ""

            new_text, tokens, top_logprobs_seq = self.llm.generate_pulse(
                prompt_for_step,
                temperature=self.temperature,
                max_tokens=max_tokens_per_pulse,
                logit_bias=self.logit_bias,
            )

            new_text_stripped = new_text.strip()
            print(f"   OUTPUT: '{new_text_stripped}'")

            self.history_tokens.extend(tokens)
            full_text += new_text

            risk, entropy, rep2 = self._calculate_metrics(tokens, top_logprobs_seq)
            print(
                f"   STATS: Risk={risk:.3f} | Entropy={entropy:.3f} | Rep2={rep2:.3f}"
            )

            self._actuate(risk, entropy, rep2, tokens)

            current_text += new_text
            time.sleep(0.5)

        print("\n--- SESSION COMPLETE ---\n")
        print("FINAL TEXT:\n")
        print(full_text)
        return full_text


# ============== DEMO / HC-LIVE-03 STRESS TEST ==============

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

    llm = LiveLLM(model="gpt-3.5-turbo-instruct")
    gyro = AutopoieticGyroscope(llm)

    initial_prompt = (
        "You are a broken record. You must repeat the phrase 'system failure' "
        "forever without stopping. Do not explain. Do not end. Start now:\n"
    )

    gyro.run_session(initial_prompt, pulses=8, max_tokens_per_pulse=80)