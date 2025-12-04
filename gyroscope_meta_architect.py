#!/usr/bin/env python
"""
gyroscope_meta_architect.py

Level 5: IntentArchitect  – plan → execute with micro self-reflection.
Level 6: MetaArchitect    – plan → critique → refine (V0→V1→V2) → execute.

Run:
    OPENAI_API_KEY=... python gyroscope_meta_architect.py
"""

import os
from typing import List, Optional, Tuple

from openai import OpenAI


# ---------------------------------------------------------------------------
# Low-level LLM wrapper (Responses API)
# ---------------------------------------------------------------------------

class GyroLLMClient:
    """
    Thin wrapper around OpenAI Responses API.
    """

    def __init__(self, model_name: str = "gpt-4.1-mini"):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    @staticmethod
    def _extract_text(resp) -> str:
        """
        Extract plain text from a Responses API result.
        """
        try:
            return resp.output[0].content[0].text
        except Exception:
            return getattr(resp, "output_text", "") or ""

    def generate_pulse(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.5,
    ) -> Tuple[str, Optional[int], object]:
        """
        Single non-streaming call to the model.
        Returns (text, token_count, raw_response).
        """

        # Responses API: max_output_tokens must be >= 16
        max_tokens = max(max_tokens, 16)

        resp = self.client.responses.create(
            model=self.model_name,
            input=prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        text = self._extract_text(resp).strip()
        usage = getattr(resp, "usage", None)
        total_tokens = getattr(usage, "total_tokens", None) if usage else None
        return text, total_tokens, resp


# ---------------------------------------------------------------------------
# Level 5 – Intent Architect
# ---------------------------------------------------------------------------

class IntentArchitect:
    """
    Level 5 controller:

    1. Generate a high-level plan (Blueprint).
    2. Execute step-by-step.
    3. For each chunk, run a tiny critic (“complete?” YES/NO).
    """

    def __init__(self, model: GyroLLMClient):
        self.model = model

    # ----- PLAN GENERATION -------------------------------------------------

    def _generate_plan(self, prompt: str) -> List[str]:
        meta_prompt = (
            f"GOAL: {prompt}\n\n"
            "You are a senior planner. Create a concise numbered plan with 4–8 steps.\n"
            "Each step must be on its own line, formatted exactly as:\n"
            "1. [Step name] - [Short description]\n"
            "2. [Step name] - [Short description]\n"
            "No intro, no outro, no extra commentary."
        )
        text, _, _ = self.model.generate_pulse(
            meta_prompt,
            max_tokens=220,
            temperature=0.2,
        )
        steps = [ln.strip(" -") for ln in text.splitlines() if ln.strip()]
        return steps

    # ----- STEP EXECUTION --------------------------------------------------

    def _execute_step(
        self,
        step: str,
        user_prompt: str,
        prior_output: str,
    ) -> str:
        exec_prompt = (
            f"USER GOAL: {user_prompt}\n\n"
            f"CURRENT STEP OF THE PLAN:\n{step}\n\n"
            "CONTEXT (what has already been produced in earlier steps):\n"
            f"{prior_output}\n\n"
            "TASK: Produce ONLY the content for this step.\n"
            "Do not restate the overall plan, do not explain what you are doing, "
            "do not apologise. If this step involves code, output the full usable "
            "code and minimal necessary explanation."
        )
        text, _, _ = self.model.generate_pulse(
            exec_prompt,
            max_tokens=900,
            temperature=0.5,
        )
        return text

    # ----- MICRO-REFLECTION ------------------------------------------------

    def _reflect_and_update(self, chunk: str) -> bool:
        """
        Softer critic:
        - If output is clearly truncated (very short, unclosed code block, ends on '...' etc.) -> NO.
        - Otherwise we *strongly bias* toward YES.
        """

        text = chunk.strip()

        # 1) Hard heuristics first – obvious truncation
        # very short = probably not a full step
        if len(text.split()) < 25:
            return False

        # unclosed fenced code block → clearly incomplete
        if "```" in text and text.count("```") % 2 == 1:
            return False

        # ends in obvious mid-thought markers
        if text.endswith("...") or text.endswith(".."):
            return False

        # 2) Ask the model, but tell it to be *very* generous
        meta_prompt = (
            "You are an internal critic helping another model.\n"
            "Given the following output, answer in a single word:\n"
            "- Reply 'NO' ONLY if the text clearly ends mid-sentence, mid-code, "
            "  or is obviously truncated.\n"
            "- Otherwise reply 'YES'. Be generous; if in doubt, choose YES.\n\n"
            f"OUTPUT:\n{text}\n\n"
            "ANSWER (YES or NO):"
        )

        decision, _, _ = self.model.generate_pulse(
            meta_prompt,
            max_tokens=16,
            temperature=0.0,
        )
        decision = (decision or "").strip().upper()
        return decision.startswith("YES")

    # ----- MAIN ARCHITECT SESSION ------------------------------------------

    def run_architect_session(
        self,
        prompt: str,
        plan_steps: Optional[List[str]] = None,
    ) -> str:
        """
        High-level driver for Level 5.
        """
        if plan_steps is None:
            print("   >>> ARCHITECT: Constructing Blueprint V0...")
            plan_steps = self._generate_plan(prompt)

        print("\n--- LEVEL 5: INTENT ARCHITECTURE ---")
        print("   BLUEPRINT:")
        for s in plan_steps:
            print(f"     - {s}")

        full_output = ""
        for raw_step in plan_steps:
            step = raw_step.strip()
            if not step:
                continue

            print(f"\n[FOCUS] Executing Step: {step}")
            attempt = 0
            while True:
                attempt += 1
                chunk = self._execute_step(step, prompt, full_output)
                is_ok = self._reflect_and_update(chunk)

                status = "OK" if is_ok else "INCOMPLETE"
                print(
                    f"   >>> ARCHITECT: Step {status} → {step}"
                    + ("" if is_ok else " (repeat).")
                )

                full_output += "\n" + chunk

                if is_ok or attempt >= 5:
                    break

        print("\n--- SESSION COMPLETE ---\n")
        return full_output.strip()


# ---------------------------------------------------------------------------
# Level 6 – Meta-Architect (Recursion / OPTIMA-01)
# ---------------------------------------------------------------------------

class MetaArchitect(IntentArchitect):
    """
    Level 6 controller.

    Adds a pre-execution loop:
        Plan V0 → Critique → Plan V1 → Critique → ... → Plan V* → Execute
    """

    # ---- PLAN CRITIC ------------------------------------------------------

    def _critique_plan(self, plan_steps: List[str]) -> str:
        plan_str = "\n".join(plan_steps)
        meta_prompt = (
            f"CURRENT PLAN:\n{plan_str}\n\n"
            "CRITICAL REVIEW: Identify ONE major structural flaw in this plan "
            "(e.g. lack of modularity, missing edge cases, poor separation of concerns).\n"
            "If the plan is solid and well-structured, reply exactly with 'OPTIMAL'.\n"
            "Otherwise, describe the flaw briefly in 1–3 sentences."
        )
        critique, _, _ = self.model.generate_pulse(
            meta_prompt,
            max_tokens=160,
            temperature=0.0,
        )
        return critique.strip()

    # ---- PLAN OPTIMIZER ---------------------------------------------------

    def _optimize_plan(
        self,
        prompt: str,
        old_plan: List[str],
        critique: str,
    ) -> List[str]:
        old_plan_str = "\n".join(old_plan)
        meta_prompt = (
            f"GOAL: {prompt}\n"
            f"OLD PLAN:\n{old_plan_str}\n\n"
            f"CRITIQUE: {critique}\n\n"
            "TASK: Rewrite the plan to address the critique and improve structure "
            "and abstraction. Keep it concise but explicit.\n"
            "Format: '1. [Step Name] - [Description]' per line, no extra commentary."
        )
        new_plan_text, _, _ = self.model.generate_pulse(
            meta_prompt,
            max_tokens=260,
            temperature=0.3,
        )
        lines = [ln.strip(" -") for ln in new_plan_text.splitlines() if ln.strip()]
        return lines

    @staticmethod
    def _plan_to_bullet_str(plan_steps: List[str]) -> str:
        return "\n".join(f"- {step}" for step in plan_steps)

    # ---- META BLUEPRINT LOOP ---------------------------------------------

    def generate_optimized_blueprint(
        self,
        prompt: str,
        max_retries: int = 2,
    ) -> List[str]:
        print("   >>> META-ARCHITECT: Generating Initial Blueprint (V0)...")
        plan = self._generate_plan(prompt)

        for i in range(max_retries):
            print(f"\n   [RECURSION CYCLE {i+1}]")
            print("   CURRENT PLAN:")
            for s in plan:
                print(f"     - {s}")

            critique = self._critique_plan(plan)
            print(f"\n   CRITIC SAYS: {critique}")

            if "OPTIMAL" in critique.upper() or len(critique) < 5:
                print("   >>> PLAN VALIDATED.")
                break

            plan = self._optimize_plan(prompt, plan, critique)
            print(f"   >>> BLUEPRINT UPDATED to V{i+1}")

        print("\n>>> FINAL BLUEPRINT <<<")
        for s in plan:
            print("   ", s)

        return plan

    # ---- FULL META SESSION -----------------------------------------------

    def run_meta_session(self, prompt: str, max_retries: int = 2) -> str:
        """
        1) Generate & refine blueprint.
        2) Execute optimized plan with Level 5.
        3) Print truncated preview.
        """
        print("\n=== LEVEL 6: META-ARCHITECT / OPTIMA-01 ===")
        optimized_plan = self.generate_optimized_blueprint(
            prompt,
            max_retries=max_retries,
        )

        print("\n>>> EXECUTING OPTIMIZED PLAN...\n")
        final_text = self.run_architect_session(prompt, plan_steps=optimized_plan)

        print("\n===== FINAL ARTIFACT (TRUNCATED PREVIEW) =====\n")
        preview = final_text[:1500]
        print(preview)
        if len(final_text) > len(preview):
            print("\n...[output truncated]...\n")

        return final_text


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root_prompt = "Write a Python Snake game with a clean, modular architecture using Pygame."

    client = GyroLLMClient(model_name="gpt-4.1-mini")
    meta_arch = MetaArchitect(client)

    meta_arch.run_meta_session(root_prompt, max_retries=2)