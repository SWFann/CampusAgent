"""Dormitory Dinner Planning scene plugin.

This plugin implements the competition's main demo scenario: four dorm-mates
negotiating where to eat dinner together. It is built on the P8 Scene Core
framework and enforces strict privacy boundaries:

- Raw preferences (including free-text notes) never leave the private domain.
- Only de-identified capsules are used for candidate generation and evaluation.
- Public results contain only aggregate scores and allowlisted reason codes.
- The model gateway is used only to polish non-sensitive structured output.
- When the model is unavailable, a deterministic rule-based path completes the
  scenario without degradation.
"""
from __future__ import annotations

from .plugin import DormDinnerPlugin

__all__ = ["DormDinnerPlugin"]
