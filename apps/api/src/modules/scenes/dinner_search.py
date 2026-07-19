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


class DebateOpening(BaseModel):
    speaker: str = "主持人Agent"
    content: str


class AgentRestaurantProposal(BaseModel):
    agent_name: str
    preference_summary: str = ""
    proposals: list[DinnerCandidate] = Field(default_factory=list)


class DebateTurn(BaseModel):
    agent_name: str
    position: str
    stance: str = "discuss"
    target_candidate_keys: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class DebateRound(BaseModel):
    round: int
    turns: list[DebateTurn] = Field(default_factory=list)
    host_summary: str = ""


class AgentPublicTurn(BaseModel):
    agent_name: str
    round: int
    search_summary: str = ""
    position: str
    source_urls: list[str] = Field(default_factory=list)


class NegotiationResult(BaseModel):
    opening: DebateOpening = Field(default_factory=lambda: DebateOpening(content="主持人Agent开始本轮宿舍聚餐协商。"))
    agent_proposals: list[AgentRestaurantProposal] = Field(default_factory=list)
    rounds: list[DebateRound] = Field(default_factory=list)
    agents: list[AgentPublicTurn] = Field(default_factory=list)
    coordinator_summary: str
    candidates: list[DinnerCandidate]


def _loads_model_json(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ValueError("model content is not JSON text")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model JSON root must be an object")
    return parsed


@dataclass(repr=False)
class StepFunDinnerProvider:
    base_url: str
    model: str
    api_key: SecretStr | str
    timeout_ms: int = 60_000
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
            "你是宿舍聚餐辩论主持系统。必须模拟主持人Agent、每个同学Agent、最终协调Agent的"
            "公开协商过程。只能从给定搜索证据中推荐真实餐厅；所有 proposal 和 final candidate "
            "的 source_urls 必须逐字匹配证据 URL。不得补造名称、地址、价格或营业时间。"
            "本演示版本允许展示成员偏好推理，但不得输出 API key、密码、token 或系统配置。只返回 JSON。"
        )
        user = {
            "city": city,
            "origin": origin,
            "topic": topic,
            "round_count": round_count,
            "host_agent": "主持人Agent",
            "coordinator_agent": "最终协调Agent",
            "members": member_preferences,
            "previous_public_memory": previous_memory[-20:],
            "search_evidence": evidence_payload,
            "output_schema": {
                "opening": {"speaker": "主持人Agent", "content": "说明参与者、目标和辩论规则"},
                "agent_proposals": [
                    {
                        "agent_name": "Alice Agent",
                        "preference_summary": "公开说明该 Agent 的偏好和约束",
                        "proposals": [
                            {
                                "candidate_key": "stable-key",
                                "display_name": "真实餐厅名",
                                "address": "证据中的地址或未核实",
                                "price_hint": "证据中的价格或未核实",
                                "business_hours_hint": "证据中的营业时间或未核实",
                                "public_reason": "为什么该 Agent 推荐它",
                                "risk_notice": "信息可能变化，请到店前确认",
                                "source_urls": ["必须来自 search_evidence.url"],
                            }
                        ],
                    }
                ],
                "rounds": [
                    {
                        "round": 1,
                        "turns": [
                            {
                                "agent_name": "Alice Agent",
                                "position": "支持、反驳或修正某个候选",
                                "stance": "support|challenge|revise|compromise",
                                "target_candidate_keys": ["stable-key"],
                                "source_urls": ["必须来自 search_evidence.url"],
                            }
                        ],
                        "host_summary": "主持人总结本轮共识和分歧",
                    }
                ],
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
                "candidate_count_rule": "最终 candidates 尽量给出 2-4 个可投票候选；每个候选必须有真实 source_urls。",
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
            parsed = _loads_model_json(content)
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            raise DinnerSearchError("智能体汇总暂时不可用，请稍后重试") from exc

        by_url = {item.url: item for item in evidence}
        def grounded_candidates(raw_candidates: Any) -> list[DinnerCandidate]:
            grounded_items: list[DinnerCandidate] = []
            for raw in raw_candidates if isinstance(raw_candidates, list) else []:
                if not isinstance(raw, dict):
                    continue
                urls = [url for url in raw.get("source_urls", []) if url in by_url]
                if not urls:
                    continue
                raw["source_urls"] = urls
                raw["sources"] = [by_url[url].model_dump() for url in urls]
                try:
                    grounded_items.append(DinnerCandidate.model_validate(raw))
                except ValidationError:
                    continue
            return grounded_items

        grounded = grounded_candidates(parsed.get("candidates", []))
        proposals: list[AgentRestaurantProposal] = []
        for raw_proposal in parsed.get("agent_proposals", []) if isinstance(parsed, dict) else []:
            if not isinstance(raw_proposal, dict):
                continue
            raw_proposal["proposals"] = grounded_candidates(raw_proposal.get("proposals", []))
            try:
                proposals.append(AgentRestaurantProposal.model_validate(raw_proposal))
            except ValidationError:
                continue

        if not grounded:
            raise DinnerSearchError("模型未生成具有可核验来源的候选")
        try:
            opening = DebateOpening.model_validate(parsed.get("opening") or {"content": "主持人Agent开始本轮宿舍聚餐协商。"})
            rounds = [DebateRound.model_validate(item) for item in parsed.get("rounds", [])]
            agents = [AgentPublicTurn.model_validate(item) for item in parsed.get("agents", [])]
            summary = str(parsed.get("coordinator_summary") or "已根据真实来源完成汇总")
        except (ValidationError, AttributeError) as exc:
            raise DinnerSearchError("智能体公开辩论格式无效") from exc
        if not agents and rounds:
            agents = [
                AgentPublicTurn(
                    agent_name=turn.agent_name,
                    round=debate_round.round,
                    position=turn.position,
                    source_urls=turn.source_urls,
                )
                for debate_round in rounds
                for turn in debate_round.turns
            ]
        final_candidates = list(grounded)
        if len(final_candidates) < 2:
            existing_keys = {candidate.candidate_key for candidate in final_candidates}
            for proposal in proposals:
                for candidate in proposal.proposals:
                    if candidate.candidate_key in existing_keys:
                        continue
                    final_candidates.append(candidate)
                    existing_keys.add(candidate.candidate_key)
                    if len(final_candidates) >= 4:
                        break
                if len(final_candidates) >= 4:
                    break
        return NegotiationResult(
            opening=opening,
            agent_proposals=proposals,
            rounds=rounds,
            agents=agents,
            coordinator_summary=summary,
            candidates=final_candidates[:4],
        )
