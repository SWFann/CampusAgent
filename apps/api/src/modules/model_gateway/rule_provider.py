"""Rule Provider — deterministic, model-free scoring for meal planning.

This provider implements a privacy-safe fallback path (P7 guide §7) used
when no model node is available. It performs deterministic rule-based
scoring of restaurant candidates against hard constraints and soft
preferences, producing stable, reproducible results.

Privacy:
- Never depends on an external model or network.
- Output ``safe_public_summary`` contains only allowlisted reason codes —
  no private preferences, thresholds, or member-identifying information.
- Used for P9 meal-planning scenarios; deterministic so tests are stable.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

from ...db.time import utc_now
from .providers import ProviderType
from .schemas import (
    CallMetadata,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderHealth,
    ProviderHealthStatus,
    ResponseContent,
)

# Allowlisted reason codes that may appear in safe_public_summary.
# These never reveal private preferences, psychological/economic labels, or
# member-identifying information (aligned with P9-10 safe public reasons).
_ALLOWED_REASON_CODES = frozenset(
    {
        "within_budget",
        "cuisine_match",
        "within_distance",
        "environment_match",
        "hard_constraint_violation",
        "no_match",
    }
)


class RuleProvider:
    """Deterministic rule-based provider for meal-planning scoring.

    The provider reads a ``preference_capsule`` from the ChatRequest (a
    de-identified summary — never raw P4 data) and a list of candidates
    encoded in the last user message as JSON, then scores each candidate
    against hard constraints and soft preferences.
    """

    def __init__(self, *, name: str = "rule") -> None:
        self.name = name
        self.provider_type = ProviderType.RULE
        self.is_external = False
        self._call_count = 0

    # ------------------------------------------------------------------
    # Scoring engine
    # ------------------------------------------------------------------

    @staticmethod
    def _stable_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_candidates(messages_text: str) -> list[dict[str, Any]]:
        """Extract candidate restaurants from the last user message.

        Expects the user message to contain a JSON array of candidate
        objects. If parsing fails, returns an empty list.
        """
        import json

        try:
            # The last message content may be JSON or contain a JSON block.
            text = messages_text.strip()
            # Try direct parse first.
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [c for c in parsed if isinstance(c, dict)]
            if isinstance(parsed, dict) and "candidates" in parsed:
                candidates = parsed["candidates"]
                if isinstance(candidates, list):
                    return [c for c in candidates if isinstance(c, dict)]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    @staticmethod
    def _check_hard_constraints(
        candidate: dict[str, Any],
        capsule: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Return (passes, reason_codes) for hard constraints.

        Hard constraints are non-negotiable: budget ceiling, excluded
        cuisines, distance limit. A violation yields a deterministic reject.
        """
        reasons: list[str] = []
        passes = True

        # Budget ceiling
        budget_tier = capsule.get("budget_tier")
        candidate_tier = candidate.get("price_tier") or candidate.get("budget_tier")
        if budget_tier and candidate_tier:
            tier_order = {"low": 0, "medium": 1, "high": 2}
            bt = tier_order.get(str(budget_tier).lower())
            ct = tier_order.get(str(candidate_tier).lower())
            if bt is not None and ct is not None and ct > bt:
                reasons.append("hard_constraint_violation")
                passes = False

        # Excluded cuisines
        excluded = capsule.get("excluded_cuisines") or []
        candidate_cuisines = candidate.get("cuisines") or []
        if excluded and candidate_cuisines and any(
            c in excluded for c in candidate_cuisines
        ):
            reasons.append("hard_constraint_violation")
            passes = False

        # Distance limit
        distance_limit = capsule.get("distance_limit_km")
        candidate_distance = candidate.get("distance_km")
        if distance_limit is not None and candidate_distance is not None:
            try:
                if float(candidate_distance) > float(distance_limit):
                    reasons.append("hard_constraint_violation")
                    passes = False
            except (TypeError, ValueError):
                pass

        if passes and not reasons:
            reasons.append("within_budget")
        return passes, reasons

    @staticmethod
    def _score_soft_preferences(
        candidate: dict[str, Any],
        capsule: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Return (score, reason_codes) for soft preferences.

        Score is in [0.0, 1.0]. Soft preferences include cuisine match,
        environment match, and distance closeness.
        """
        score = 0.0
        reasons: list[str] = []
        max_points = 0.0

        # Cuisine preference match
        preferred_cuisines = capsule.get("cuisine_preferences") or []
        candidate_cuisines = candidate.get("cuisines") or []
        max_points += 1.0
        if preferred_cuisines and candidate_cuisines:
            matches = len(set(preferred_cuisines) & set(candidate_cuisines))
            if matches > 0:
                score += min(1.0, matches / max(1, len(preferred_cuisines)))
                reasons.append("cuisine_match")

        # Environment match
        env_pref = capsule.get("environment_preference")
        candidate_env = candidate.get("environment")
        max_points += 1.0
        if env_pref and candidate_env and str(env_pref).lower() == str(candidate_env).lower():
            score += 1.0
            reasons.append("environment_match")

        # Distance closeness (closer = higher score)
        distance_limit = capsule.get("distance_limit_km")
        candidate_distance = candidate.get("distance_km")
        max_points += 1.0
        if distance_limit is not None and candidate_distance is not None:
            try:
                ratio = 1.0 - (
                    float(candidate_distance) / max(1.0, float(distance_limit))
                )
                score += max(0.0, min(1.0, ratio))
                reasons.append("within_distance")
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # Normalise to [0, 1]
        normalised = score / max(1.0, max_points) if max_points > 0 else 0.0
        return round(normalised, 4), reasons

    def _score_candidates(
        self,
        candidates: list[dict[str, Any]],
        capsule: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Score all candidates and return ranked results.

        Each result contains: id, name, score, passes_hard, reason_codes,
        safe_public_summary. Reason codes are filtered to the allowlist.
        """
        results: list[dict[str, Any]] = []
        for candidate in candidates:
            passes, hard_reasons = self._check_hard_constraints(candidate, capsule)
            if not passes:
                soft_score = 0.0
                soft_reasons: list[str] = []
            else:
                soft_score, soft_reasons = self._score_soft_preferences(candidate, capsule)

            all_reasons = hard_reasons + soft_reasons
            safe_reasons = [r for r in all_reasons if r in _ALLOWED_REASON_CODES]

            # Build a safe public summary using only allowlisted codes.
            if passes:
                summary = "符合基本要求"
                if "cuisine_match" in safe_reasons:
                    summary += "，菜系匹配"
                if "within_distance" in safe_reasons:
                    summary += "，距离合适"
            else:
                summary = "不满足硬性约束"

            results.append(
                {
                    "id": candidate.get("id", candidate.get("name", "unknown")),
                    "name": candidate.get("name", "未命名候选"),
                    "score": soft_score if passes else 0.0,
                    "passes_hard": passes,
                    "reason_codes": safe_reasons,
                    "safe_public_summary": summary,
                }
            )

        # Stable sort: passes first, then by score descending, then by id
        # for deterministic ordering.
        results.sort(
            key=lambda r: (not r["passes_hard"], -r["score"], str(r["id"]))
        )
        return results

    # ------------------------------------------------------------------
    # ModelProvider protocol
    # ------------------------------------------------------------------

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Score candidates using deterministic rules."""
        self._call_count += 1
        start = time.perf_counter()
        request_id = request.request_id or f"rule-{self._call_count}"

        capsule = request.preference_capsule or {}
        last_user_text = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_text = msg.content
                break

        candidates = self._parse_candidates(last_user_text)
        scored = self._score_candidates(candidates, capsule)

        content_obj: dict[str, Any] = {
            "candidates": scored,
            "count": len(scored),
            "engine": "rule",
        }
        if not scored:
            content_obj["reason_codes"] = ["no_match"]

        latency_ms = int((time.perf_counter() - start) * 1000)
        prompt_tokens = sum(len(m.content) // 4 + 1 for m in request.messages)

        return ChatResponse(
            request_id=request_id,
            model=request.model or "rule-engine",
            status="completed",
            response=ResponseContent(type="STRUCTURED", content=content_obj),
            metadata=CallMetadata(
                prompt_tokens=prompt_tokens,
                completion_tokens=len(scored),
                latency_ms=latency_ms,
                provider=self.name,
                model=request.model or "rule-engine",
            ),
        )

    def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Rule provider returns a deterministic hash-based pseudo-embedding."""
        self._call_count += 1
        start = time.perf_counter()
        dimension = request.dimension or 8
        digest = self._stable_hash(request.text)
        values: list[float] = []
        for i in range(dimension):
            byte_val = int(digest[(i % len(digest))], 16)
            values.append((byte_val / 15.0) * 2.0 - 1.0)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return EmbeddingResponse(
            request_id=request.request_id,
            model=request.model or "rule-embedding",
            status="completed",
            embedding=values,
            dimension=dimension,
            metadata=CallMetadata(
                prompt_tokens=len(request.text) // 4 + 1,
                completion_tokens=None,
                latency_ms=latency_ms,
                provider=self.name,
                model=request.model or "rule-embedding",
            ),
        )

    def health(self) -> ProviderHealth:
        """Rule provider is always online (pure compute, no I/O)."""
        return ProviderHealth(
            provider_name=self.name,
            healthy=True,
            status=ProviderHealthStatus.ONLINE,
            latency_ms=0,
            last_checked=utc_now().isoformat(),
        )

    @property
    def call_count(self) -> int:
        return self._call_count

    def __repr__(self) -> str:
        return f"<RuleProvider name={self.name}>"
