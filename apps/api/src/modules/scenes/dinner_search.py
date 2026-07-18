"""Evidence-first StepFun search and dinner negotiation adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError


class DinnerSearchError(RuntimeError):
    """Raised when real search or grounded model output is unavailable."""


class SearchEvidence(BaseModel):
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    indexed_at: str | None = None
    retrieved_at: datetime


class DinnerCandidate(BaseModel):
    candidate_key: str
    display_name: str
    address: str = "未核实"
    price_hint: str = "未核实"
    business_hours_hint: str = "未核实"
    public_reason: str
    risk_notice: str = "信息可能变化，请到店前确认"
    source_urls: list[str] = Field(default_factory=list, exclude=True)
    sources: list[SearchEvidence] = Field(default_factory=list)


class AgentPublicTurn(BaseModel):
    agent_name: str
    round: int
    search_summary: str = ""
    position: str
    source_urls: list[str] = Field(default_factory=list)


class NegotiationResult(BaseModel):
    agents: list[AgentPublicTurn] = Field(default_factory=list)
    coordinator_summary: str
    candidates: list[DinnerCandidate]


@dataclass(repr=False)
class StepFunDinnerProvider:
    base_url: str
    model: str
    api_key: SecretStr | str
    timeout_ms: int = 30_000
    transport: httpx.BaseTransport | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not isinstance(self.api_key, SecretStr):
            self.api_key = SecretStr(self.api_key)

    def __repr__(self) -> str:
        return (
            f"StepFunDinnerProvider(base_url={self.base_url!r}, "
            f"model={self.model!r}, api_key=SecretStr('**********'))"
        )

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=httpx.Timeout(self.timeout_ms / 1000),
            transport=self.transport,
        )

    def _headers(self) -> dict[str, str]:
        assert isinstance(self.api_key, SecretStr)
        return {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    def search(self, query: str, limit: int = 10) -> list[SearchEvidence]:
        try:
            with self._client() as client:
                response = client.post(
                    f"{self.base_url}/search",
                    headers=self._headers(),
                    json={"query": query, "n": max(1, min(limit, 20))},
                )
            response.raise_for_status()
            raw_results = response.json().get("results", [])
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise DinnerSearchError("真实地点搜索暂时不可用，请稍后重试") from exc

        retrieved_at = datetime.now(UTC)
        evidence: list[SearchEvidence] = []
        for item in raw_results if isinstance(raw_results, list) else []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            if not url.startswith("https://") or not title:
                continue
            evidence.append(
                SearchEvidence(
                    title=title[:300],
                    url=url,
                    snippet=str(item.get("snippet") or "")[:2000],
                    content=str(item.get("content") or "")[:6000],
                    indexed_at=str(item.get("time")) if item.get("time") else None,
                    retrieved_at=retrieved_at,
                )
            )
        return evidence

    def negotiate(
        self,
        *,
        city: str,
        origin: str,
        topic: str,
        round_count: int,
        member_preferences: list[dict[str, Any]],
        previous_memory: list[dict[str, Any]],
        evidence: list[SearchEvidence],
    ) -> NegotiationResult:
        if not 1 <= round_count <= 10:
            raise ValueError("round_count must be between 1 and 10")
        if not evidence:
            raise DinnerSearchError("没有找到可核验的真实地点来源")

        evidence_payload = [item.model_dump(mode="json") for item in evidence]
        system = (
            "你是聚餐协调Agent。只能从给定搜索证据中推荐真实餐厅；候选的每个 source_urls "
            "必须逐字匹配证据 URL。不得补造名称、地址、价格或营业时间。成员原始私密输入不得复述，"
            "只输出脱敏公开观点。只返回 JSON。"
        )
        user = {
            "city": city,
            "origin": origin,
            "topic": topic,
            "round_count": round_count,
            "members": member_preferences,
            "previous_public_memory": previous_memory[-20:],
            "search_evidence": evidence_payload,
            "output_schema": {
                "agents": [{"agent_name": "成员A Agent", "round": 1, "search_summary": "", "position": "", "source_urls": []}],
                "coordinator_summary": "",
                "candidates": [{
                    "candidate_key": "stable-key",
                    "display_name": "",
                    "address": "未核实",
                    "price_hint": "未核实",
                    "business_hours_hint": "未核实",
                    "public_reason": "",
                    "risk_notice": "信息可能变化，请到店前确认",
                    "source_urls": [],
                }],
            },
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            with self._client() as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            raise DinnerSearchError("智能体汇总暂时不可用，请稍后重试") from exc

        by_url = {item.url: item for item in evidence}
        grounded: list[DinnerCandidate] = []
        for raw in parsed.get("candidates", []) if isinstance(parsed, dict) else []:
            if not isinstance(raw, dict):
                continue
            urls = [url for url in raw.get("source_urls", []) if url in by_url]
            if not urls:
                continue
            raw["source_urls"] = urls
            raw["sources"] = [by_url[url].model_dump() for url in urls]
            try:
                grounded.append(DinnerCandidate.model_validate(raw))
            except ValidationError:
                continue

        if not grounded:
            raise DinnerSearchError("模型未生成具有可核验来源的候选")
        try:
            agents = [AgentPublicTurn.model_validate(item) for item in parsed.get("agents", [])]
            summary = str(parsed.get("coordinator_summary") or "已根据真实来源完成汇总")
        except (ValidationError, AttributeError) as exc:
            raise DinnerSearchError("智能体公开辩论格式无效") from exc
        return NegotiationResult(
            agents=agents,
            coordinator_summary=summary,
            candidates=grounded[:4],
        )
