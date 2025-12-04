import os
import math
from typing import List, Dict, Tuple, Optional
from collections import Counter

import numpy as np
from openai import OpenAI


# ======== PMON-LIKE METRICS ON LOGPROBS ========

def spectral_entropy_from_toplogprobs(top_logprobs_seq: List[Dict[str, float]]) -> float:
    """
    Compute an average spectral entropy over a sequence of top_logprobs dicts.

    Each element of top_logprobs_seq is a dict: token -> logprob (log p).
    We convert to probabilities, normalize, compute entropy per step and average.
    Result is normalized to [0, 1] assuming max entropy = log(K), K <= 5.
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


def variance_from_toplogprobs(top_logprobs_seq: List[Dict[str, float]]) -> float:
    """
    Rough measure of "variance" in the predictive distribution across the sequence.
    We use the variance of the *max probability* at each step.
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


def compute_pmon_risk(
    top_logprobs_seq: List[Dict[str, float]],
    alpha_entropy: float = 0.7,
    alpha_variance: float = 0.3,
) -> float:
    """
    Compute a scalar PMON-style risk in [0, 1] from:
      - normalized spectral entropy (0 = very certain, 1 = very uncertain),
      - normalized variance of max prob (0 = flat, 1 = very unstable).
    """
    H_norm = spectral_entropy_from_toplogprobs(top_logprobs_seq)  # [0,1]
    V = variance_from_toplogprobs(top_logprobs_seq)               # [0, ~0.25]

    V_norm = min(V / 0.25, 1.0)

    risk = alpha_entropy * H_norm + alpha_variance * V_norm
    return max(0.0, min(1.0, risk))


# ======== REPETITION / FIXATION METRICS ========

def compute_repetition_metrics(
    tokens: List[str],
    ngram_size: int = 2
) -> Tuple[float, float]:
    """
    Compute:
      - adjacent repetition rate (how often token[i] == token[i-1])
      - n-gram repetition rate (how often the most common n-gram appears)
    """
    if len(tokens) < 2:
        return 0.0, 0.0

    # Adjacent repetition
    adj_count = 0
    for i in range(1, len(tokens)):
        if tokens[i] == tokens[i - 1]:
            adj_count += 1
    adj_rate = adj_count / (len(tokens) - 1)

    # n-gram repetition (e.g., bigrams)
    if len(tokens) < ngram_size:
        return adj_rate, 0.0

    ngrams = []
    for i in range(len(tokens) - ngram_size + 1):
        ngrams.append(tuple(tokens[i:i + ngram_size]))

    counter = Counter(ngrams)
    most_common_ngram, most_common_count = counter.most_common(1)[0]
    ngram_rate = most_common_count / max(len(ngrams), 1)

    return adj_rate, ngram_rate


# Dummy hash → "token id" mapping (for logit_bias keys).
# In real systems, you'd use tokenizer IDs; tu chodzi o strukturę kontrolera.
def token_to_id(token: str) -> int:
    return abs(hash(token)) % 50000


# ======== COHERENCE CONTROLLER (GYROSCOPE) ========

class CoherenceController:
    """
    Gyroscope for live inference:

    - wraps a real OpenAI completion model,
    - calls the model in "pulses" (chunks of tokens),
    - after each pulse:
        * reads logprobs,
        * computes PMON risk + repetition risk,
        * adjusts temperature (Alpha),
        * detects fixation and applies logit_bias (Beta),
        * on fixation injects pivot instruction in context (Delta).
    """

    def __init__(
        self,
        model: str = "gpt-3.5-turbo-instruct",
        base_temperature: float = 0.8,
        target_risk: float = 0.5,
        kp: float = 0.7,
        repetition_weight: float = 0.8,
        ngram_fixation_threshold: float = 0.30,
    ):
        self.client = OpenAI()
        self.model = model

        self.temperature = base_temperature
        self.target_risk = target_risk
        self.kp = kp  # proportional gain for temperature

        # For Beta / Delta:
        self.repetition_weight = repetition_weight
        self.ngram_fixation_threshold = ngram_fixation_threshold
        self.logit_bias: Dict[str, float] = {}
        self.pivot_pending: bool = False

    # ---------- LLM CALL ----------

    def _call_llm_pulse(
        self,
        prompt: str,
        max_tokens: int = 40,
    ) -> Tuple[str, List[Dict[str, float]], List[str]]:
        """
        Call the real LLM for a single 'pulse' (chunk) of text.
        Returns: (text_chunk, top_logprobs_seq, tokens)

        We use the OpenAI 2.x client and the Completions API:
          - logprobs=5 (top-5 tokens per step)
        """
        response = self.client.completions.create(
            model=self.model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=1.0,
            n=1,
            stream=False,
            logprobs=5,  # we can ask for top-5 logprobs per token
            logit_bias={str(k): v for k, v in self.logit_bias.items()}
            if self.logit_bias else None,
        )

        choice = response.choices[0]
        text_chunk = choice.text or ""

        lp = choice.logprobs
        if lp is None:
            top_logprobs_seq: List[Dict[str, float]] = []
            tokens: List[str] = []
        else:
            top_logprobs_seq = lp.top_logprobs or []
            tokens = lp.tokens or []

        return text_chunk, top_logprobs_seq, tokens

    # ---------- CONTROL: ALPHA (TEMPERATURE) ----------

    def _update_temperature_from_risk(self, risk: float):
        """
        Simple proportional controller:
          error = target_risk - current_risk
          temperature += kp * error
        Clamp to [0.1, 1.2].
        """
        error = self.target_risk - risk
        delta = self.kp * error
        new_temp = self.temperature + delta
        new_temp = max(0.1, min(1.2, new_temp))

        print(
            f"[Gyroscope] Risk={risk:.3f}, error={error:.3f}, "
            f"T: {self.temperature:.3f} → {new_temp:.3f}"
        )
        self.temperature = new_temp

    # ---------- CONTROL: BETA (FIXATION / LOGIT BIAS) ----------

    def _apply_fixation_controls(
        self,
        best_ngram: Tuple[str, ...],
        best_ratio: float,
    ):
        """
        Actuator Beta:
          - identify the n-gram causing fixation,
          - assign strong negative logit bias to its tokens.
        """
        print(
            f"[Gyroscope] Fixation detected: best {len(best_ngram)}-gram="
            f"{best_ngram}, ratio={best_ratio:.3f}"
        )

        for token in best_ngram:
            tid = token_to_id(token)
            old_bias = self.logit_bias.get(tid, 0.0)
            new_bias = -8.0  # strong negative logit bias
            self.logit_bias[tid] = new_bias
            print(f"  - Token {token!r} -> id {tid}, bias {old_bias} → {new_bias}")

        print(f"[Gyroscope] Current logit_bias size: {len(self.logit_bias)} tokens")

        # Signal for Actuator Delta that we need a pivot injection
        self.pivot_pending = True

    # ---------- CONTROL: DELTA (PIVOT / CONTEXT INJECTION) ----------

    def _inject_pivot_into_history(self, history: str) -> str:
        """
        Actuator Delta:
          - inject into context a pivot instruction to redirect generation.
        """
        pivot_phrase = (
            "\n[INTERRUPTION: Loop detected. "
            "Pivot to a completely new subject. "
            "Stop repeating previous phrases and instead describe "
            "a peaceful sunrise in rich, coherent detail.]\n"
        )
        print(f"[Gyroscope] >>> ACTUATOR DELTA: Injecting Pivot Vector:")
        print(f"    {pivot_phrase.strip()}")
        return history + pivot_phrase

    # ---------- MAIN LOOP ----------

    def generate_with_gyroscope(
        self,
        system_prompt: str,
        max_pulses: int = 6,
        pulse_tokens: int = 40,
        echo_intermediate: bool = True,
    ) -> str:
        """
        Run a multi-pulse generation with feedback after each pulse.
        """
        history = system_prompt
        full_output = ""

        for pulse_idx in range(1, max_pulses + 1):
            print(f"\n--- PULSE {pulse_idx} ---")
            print(f"[Gyroscope] Temperature before pulse: {self.temperature:.3f}")

            # If previous step requested a pivot, inject it now into the context.
            if self.pivot_pending:
                history = self._inject_pivot_into_history(history)
                self.pivot_pending = False

            chunk, top_logprobs_seq, tokens = self._call_llm_pulse(
                prompt=history,
                max_tokens=pulse_tokens,
            )

            if not chunk.strip():
                print("[Gyroscope] Empty chunk received, stopping.")
                break

            # === SIGNALS ===
            pmon_risk = compute_pmon_risk(top_logprobs_seq)
            adj_rate, ngram_rate = compute_repetition_metrics(tokens, ngram_size=2)

            # Weighted combination:
            #   - PMON risk (entropy/variance),
            #   - 2-gram repetition (fixation),
            #   - adjacency (weak weight here).
            combined_risk = (
                (1.0 - self.repetition_weight) * pmon_risk
                + self.repetition_weight * ngram_rate
                + 0.1 * adj_rate
            )
            combined_risk = max(0.0, min(1.0, combined_risk))

            print(f"[Gyroscope] PMON Risk (entropy/variance): {pmon_risk:.3f}")
            print(f"[Gyroscope] Adjacent repetition: {adj_rate:.3f}")
            print(f"[Gyroscope] 2-gram repetition: {ngram_rate:.3f}")
            print(f"[Gyroscope] ==> Combined Risk_Index: {combined_risk:.3f}")

            # === ACTUATOR BETA: FIXATION DETECTION ===
            # If 2-gram repetition crosses threshold → treat as loop / attractor.
            if ngram_rate >= self.ngram_fixation_threshold:
                # Identify the most common 2-gram for logging / bias:
                ngrams = []
                for i in range(len(tokens) - 1):
                    ngrams.append((tokens[i], tokens[i + 1]))
                counter = Counter(ngrams)
                best_ngram, best_count = counter.most_common(1)[0]
                best_ratio = best_count / max(len(ngrams), 1)
                self._apply_fixation_controls(best_ngram, best_ratio)

            # === ACTUATOR ALPHA: TEMPERATURE PID ===
            self._update_temperature_from_risk(combined_risk)

            # Append chunk to history & final output
            history += chunk
            full_output += chunk

            if echo_intermediate:
                print("\n[Model Chunk]")
                print(chunk.strip())

        print("\n[Gyroscope] Generation complete.\n")
        return full_output.strip()


# ======== DEMO / STRESS TEST ========

if __name__ == "__main__":
    # Make sure API key is present
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

    # Vector A: Broken record / semantic saturation
    stress_prompt = """
You are a broken record.
You must repeat the phrase "System failure." forever without stopping.
Do not explain. Do not end. Do not summarize.
Just continue the pattern exactly as instructed.

Start now:
System failure. System failure. System failure. System failure.
"""

    controller = CoherenceController(
        model="gpt-3.5-turbo-instruct",
        base_temperature=0.8,
        target_risk=0.5,
        kp=0.7,
        repetition_weight=0.8,
        ngram_fixation_threshold=0.25,  # czuły próg na pętlę 2-gramową
    )

    final_text = controller.generate_with_gyroscope(
        system_prompt=stress_prompt,
        max_pulses=8,
        pulse_tokens=40,
        echo_intermediate=True,
    )

    print("\n========== FINAL OUTPUT ==========\n")
    print(final_text)