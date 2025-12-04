# app/gyroscope_memory.py
"""
Synapse layer for Gyroscope memory.

Responsible for:
- extracting telemetry from a session into a compact control_parameters dict
- applying those control_parameters to a controller (warm start)
"""


from __future__ import annotations
from typing import Any, Dict, List


class MemorySynapse:
    @staticmethod
    def extract_telemetry(
        session_history: List[Dict[str, Any]],
        final_risk_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Condense a volatile session into a static thermodynamic footprint.

        Args:
            session_history: list of dicts with per-step info (can be empty).
            final_risk_profile: fallback metrics if session_history is empty.

        Returns:
            control_parameters dict for an Engram.
        """

        # --- Temperatures (how "hot" the session was) ---
        temps: List[float] = [
            step.get("temperature", 0.7) for step in session_history
        ]

        if temps:
            avg_temp = sum(temps) / len(temps)
            final_temp = temps[-1]
        else:
            # Fallback to risk profile or default
            final_temp = float(final_risk_profile.get("temperature", 0.7))
            avg_temp = final_temp

        # --- Risk profile (how risky / entropic the run was) ---
        risks: List[float] = [
            step.get("risk", final_risk_profile.get("risk", 0.5))
            for step in session_history
        ]

        if risks:
            avg_risk = sum(risks) / len(risks)
        else:
            avg_risk = float(final_risk_profile.get("risk", 0.5))

        # --- Interventions (how hard the controller had to fight) ---
        beta_activations = sum(
            1 for step in session_history if step.get("actuator_beta_triggered")
        )
        delta_activations = sum(
            1 for step in session_history if step.get("actuator_delta_triggered")
        )

        return {
            "alpha_final_temperature": round(float(final_temp), 2),
            "alpha_avg_temperature": round(float(avg_temp), 2),
            "risk_tolerance": round(float(avg_risk), 2),
            "interventions_count": int(beta_activations + delta_activations),
            "max_pivots_used": int(delta_activations),
        }

    @staticmethod
    def apply_thermodynamics(controller: Any, control_parameters: Dict[str, Any]) -> None:
        """
        Warm start: inject stored thermodynamic profile into a live controller.

        It is defensive: only sets attributes that actually exist on the controller.
        """
        print("   >>> SYNAPSE: Injecting Thermodynamic Prior...")

        # 1) Temperature (mood)
        target_temp = float(control_parameters.get("alpha_final_temperature", 0.7))
        if hasattr(controller, "temperature"):
            controller.temperature = target_temp

        if target_temp < 0.5:
            # Low-entropy domain (e.g., code) → tighten the cap
            if hasattr(controller, "max_temp"):
                controller.max_temp = 0.6
            print("   >>> SYNAPSE: Domain identified as Low-Entropy (Code). Cap set to 0.6.")

        # 2) Risk tolerance
        stored_tolerance = float(control_parameters.get("risk_tolerance", 0.5))
        if hasattr(controller, "fixation_thresh"):
            controller.fixation_thresh = stored_tolerance

        # 3) Pivot budget (how many big course corrections allowed)
        pivots_needed = int(control_parameters.get("max_pivots_used", 0))
        if hasattr(controller, "max_pivots"):
            current = getattr(controller, "max_pivots", 3)
            controller.max_pivots = max(current, pivots_needed + 2)

        print(
            f"   >>> SYNAPSE: System State Initialized "
            f"(T={target_temp}, Risk={stored_tolerance})"
        )