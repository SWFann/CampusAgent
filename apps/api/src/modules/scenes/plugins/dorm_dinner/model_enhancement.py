"""P9-11: Model enhancement for the dorm dinner scenario.

The model gateway is used ONLY to polish the final public summary text.
It receives only non-sensitive, structured data:
- Restaurant name
- Aggregate score
- Allowlisted reason codes
- Public tags

The model NEVER sees:
- Raw preferences
- Capsules with user IDs
- Private evaluations
- Notes (free-text)

If the model call fails (timeout, error, unavailable), the rule-based
text from the aggregation phase is used as a fallback. The scenario
must work completely offline without any model calls.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("campus_agent.scenes.dorm_dinner.model_enhancement")


def build_model_prompt(
    ranked_candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build a safe model prompt containing only non-sensitive data.

    The prompt includes:
    - Restaurant names (public)
    - Aggregate scores (public)
    - Allowlisted reason codes (public)
    - Public tags (public)

    The prompt NEVER includes:
    - Individual preferences or evaluations
    - Capsule data
    - Notes or free-text
    - User identifiers
    """
    # Build a sanitised description of each candidate.
    candidate_descriptions = []
    for c in ranked_candidates[:3]:  # Only top 3 for the prompt.
        name = c.get("candidate_key", "unknown")
        score = c.get("score", 0.0)
        reason = c.get("public_reason", "")
        candidate_descriptions.append(
            f"Restaurant: {name}, Score: {score:.2f}, Reasons: {reason}"
        )

    candidates_text = "\n".join(candidate_descriptions)

    system_prompt = (
        "You are a helpful assistant that writes a brief, friendly "
        "dinner recommendation summary for a group of dorm-mates. "
        "Write in Chinese. Keep it under 100 characters. "
        "Do not mention any individual's preferences or restrictions. "
        "Only use the provided restaurant names and reasons."
    )

    user_prompt = (
        f"Here are the top ranked dinner options for the group:\n\n"
        f"{candidates_text}\n\n"
        f"Please write a brief, friendly recommendation summary."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_safe_response_schema() -> dict[str, Any]:
    """Build a JSON schema for structured model output.

    The model is asked to return a structured response with a single
    ``summary`` field. This prevents the model from injecting
    unexpected content.
    """
    return {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "maxLength": 200,
                "description": "A brief, friendly recommendation summary in Chinese.",
            }
        },
        "required": ["summary"],
        "additionalProperties": False,
    }


def enhance_public_summary(
    ranked_result: dict[str, Any],
    facade: Any,
) -> str:
    """Enhance the public summary using the model gateway.

    This function calls the model gateway to polish the rule-based
    summary text. If the model is unavailable, fails, or returns
    invalid output, the original rule-based summary is used.

    Privacy:
    - Only restaurant names, scores, and allowlisted reason codes are
      sent to the model.
    - No raw preferences, capsules, evaluations, or notes are included.
    - The model's output is validated against a strict schema.

    Args:
        ranked_result: The ranked result dict from build_ranked_result().
        facade: The SceneServiceFacade for calling the model gateway.

    Returns:
        An enhanced public summary string. If enhancement fails, the
        original rule-based summary is returned.
    """
    original_summary: str = str(ranked_result.get("public_summary", ""))
    ranked_candidates = ranked_result.get("ranked_candidates", [])

    if not ranked_candidates:
        return original_summary

    try:
        messages = build_model_prompt(ranked_candidates)
        response_schema = build_safe_response_schema()

        response = facade.model_chat(
            messages=messages,
            purpose="dinner_summary_enhancement",
            data_classification="P0",  # Only public data is sent.
            response_schema=response_schema,
        )

        # Extract the summary from the structured response.
        content = response.get("content")
        if isinstance(content, dict):
            enhanced = content.get("summary", "")
        elif isinstance(content, str):
            # Try to parse as JSON.
            import json

            try:
                parsed = json.loads(content)
                enhanced = parsed.get("summary", "") if isinstance(parsed, dict) else content
            except (json.JSONDecodeError, TypeError):
                enhanced = content
        else:
            enhanced = ""

        # Validate: must be a non-empty string, max 200 chars.
        if enhanced and isinstance(enhanced, str) and len(enhanced) <= 200:
            # Defence-in-depth: check for forbidden patterns.
            from .reasons import check_reason_for_leaks

            if check_reason_for_leaks(enhanced):
                return enhanced

        # Fall through to original if validation fails.
        logger.info(
            "dorm_dinner.model_enhancement.fallback",
            extra={"reason": "validation_failed"},
        )
        return original_summary

    except Exception as exc:
        logger.info(
            "dorm_dinner.model_enhancement.fallback",
            extra={"reason": "model_error", "error": str(exc)},
        )
        return original_summary
