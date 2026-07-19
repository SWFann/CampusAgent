from __future__ import annotations

import json

import httpx

from src.modules.scenes.dinner_search import StepFunDinnerProvider


def test_search_filters_non_https_and_preserves_evidence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search"
        assert request.headers["Authorization"] == "Bearer test-secret"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "真实餐厅",
                        "url": "https://example.com/restaurant",
                        "snippet": "上海市杨浦区，约 60 元/人",
                        "content": "营业中的餐厅页面",
                        "time": "2026-07-18",
                    },
                    {"title": "不安全链接", "url": "http://example.com/insecure"},
                ]
            },
        )

    provider = StepFunDinnerProvider(
        base_url="https://api.stepfun.com/v1",
        model="step-3.7-flash",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )

    results = provider.search("上海 复旦大学 聚餐", limit=5)

    assert len(results) == 1
    assert results[0].title == "真实餐厅"
    assert results[0].url == "https://example.com/restaurant"
    assert "test-secret" not in repr(provider)


def test_recommendations_must_reference_search_evidence() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.path == "/v1/search":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "真实餐厅页面",
                            "url": "https://example.com/real",
                            "snippet": "真实餐厅位于复旦大学附近",
                            "content": "人均 50 元",
                        }
                    ]
                },
            )
        payload = json.loads(request.content)
        assert payload["model"] == "step-3.7-flash"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "agents": [],
                                    "coordinator_summary": "仅保留可核验地点",
                                    "candidates": [
                                        {
                                            "candidate_key": "fake",
                                            "display_name": "虚构餐厅",
                                            "address": "未知",
                                            "price_hint": "未核实",
                                            "business_hours_hint": "未核实",
                                            "public_reason": "模型编造",
                                            "risk_notice": "",
                                            "source_urls": ["https://invalid.example/fake"],
                                        },
                                        {
                                            "candidate_key": "real",
                                            "display_name": "真实餐厅",
                                            "address": "复旦大学附近",
                                            "price_hint": "约 50 元",
                                            "business_hours_hint": "未核实",
                                            "public_reason": "来源可核验",
                                            "risk_notice": "信息可能变化，请到店前确认",
                                            "source_urls": ["https://example.com/real"],
                                        },
                                    ],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    provider = StepFunDinnerProvider(
        base_url="https://api.stepfun.com/v1",
        model="step-3.7-flash",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    evidence = provider.search("上海 复旦大学 聚餐")
    result = provider.negotiate(
        city="上海",
        origin="复旦大学",
        topic="宿舍聚餐",
        round_count=2,
        member_preferences=[{"agent_name": "成员A Agent", "preferences": {"budget_max": 60}}],
        previous_memory=[],
        evidence=evidence,
    )

    assert calls == 2
    assert [candidate.display_name for candidate in result.candidates] == ["真实餐厅"]
    assert result.candidates[0].sources[0].url == "https://example.com/real"


def test_negotiate_accepts_json_wrapped_in_markdown_fence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/search":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "真实餐厅页面",
                            "url": "https://example.com/real",
                            "snippet": "真实餐厅位于学校附近",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "```json\n"
                            + json.dumps(
                                {
                                    "agents": [],
                                    "coordinator_summary": "已汇总",
                                    "candidates": [
                                        {
                                            "candidate_key": "real",
                                            "display_name": "真实餐厅",
                                            "address": "学校附近",
                                            "price_hint": "约 50 元",
                                            "business_hours_hint": "未核实",
                                            "public_reason": "来源可核验",
                                            "source_urls": ["https://example.com/real"],
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            )
                            + "\n```"
                        }
                    }
                ]
            },
        )

    provider = StepFunDinnerProvider(
        base_url="https://api.stepfun.com/v1",
        model="step-3.7-flash",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    evidence = provider.search("广州 暨南大学 聚餐")

    result = provider.negotiate(
        city="广州",
        origin="暨南大学",
        topic="宿舍聚餐",
        round_count=2,
        member_preferences=[],
        previous_memory=[],
        evidence=evidence,
    )

    assert result.coordinator_summary == "已汇总"
    assert result.candidates[0].display_name == "真实餐厅"


def test_negotiate_parses_hosted_multi_agent_debate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/search":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "校外川菜馆",
                            "url": "https://example.com/sichuan",
                            "snippet": "适合多人聚餐，人均 55 元",
                        },
                        {
                            "title": "粤菜小馆",
                            "url": "https://example.com/cantonese",
                            "snippet": "距离学校近，人均 45 元",
                        },
                    ]
                },
            )
        payload = json.loads(request.content)
        prompt = payload["messages"][1]["content"]
        assert "host_agent" in prompt
        assert "agent_proposals" in prompt
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "opening": {
                                        "speaker": "主持人Agent",
                                        "content": "本轮由 Alice Agent 和 Bob Agent 分别提出候选并辩论。",
                                    },
                                    "agent_proposals": [
                                        {
                                            "agent_name": "Alice Agent",
                                            "preference_summary": "预算 30-60，偏川菜。",
                                            "proposals": [
                                                {
                                                    "candidate_key": "sichuan",
                                                    "display_name": "校外川菜馆",
                                                    "address": "学校西门外",
                                                    "price_hint": "人均 55 元",
                                                    "business_hours_hint": "晚餐营业",
                                                    "public_reason": "符合预算和口味。",
                                                    "source_urls": ["https://example.com/sichuan"],
                                                }
                                            ],
                                        },
                                        {
                                            "agent_name": "Bob Agent",
                                            "preference_summary": "预算 30-60，希望距离近。",
                                            "proposals": [
                                                {
                                                    "candidate_key": "cantonese",
                                                    "display_name": "粤菜小馆",
                                                    "address": "学校附近",
                                                    "price_hint": "人均 45 元",
                                                    "business_hours_hint": "晚餐营业",
                                                    "public_reason": "距离更近。",
                                                    "source_urls": ["https://example.com/cantonese"],
                                                }
                                            ],
                                        },
                                    ],
                                    "rounds": [
                                        {
                                            "round": 1,
                                            "turns": [
                                                {
                                                    "agent_name": "Alice Agent",
                                                    "position": "我支持校外川菜馆，预算匹配且适合多人。",
                                                    "stance": "support",
                                                    "target_candidate_keys": ["sichuan"],
                                                    "source_urls": ["https://example.com/sichuan"],
                                                },
                                                {
                                                    "agent_name": "Bob Agent",
                                                    "position": "我质疑距离，但认可价格，建议比较粤菜小馆。",
                                                    "stance": "challenge",
                                                    "target_candidate_keys": ["sichuan", "cantonese"],
                                                    "source_urls": ["https://example.com/cantonese"],
                                                },
                                            ],
                                            "host_summary": "两位 Agent 分歧在距离和口味，两个候选都保留。",
                                        }
                                    ],
                                    "coordinator_summary": "综合预算、距离和口味，保留两个真实来源候选。",
                                    "candidates": [
                                        {
                                            "candidate_key": "sichuan",
                                            "display_name": "校外川菜馆",
                                            "address": "学校西门外",
                                            "price_hint": "人均 55 元",
                                            "business_hours_hint": "晚餐营业",
                                            "public_reason": "预算和聚餐氛围更匹配。",
                                            "source_urls": ["https://example.com/sichuan"],
                                        },
                                        {
                                            "candidate_key": "cantonese",
                                            "display_name": "粤菜小馆",
                                            "address": "学校附近",
                                            "price_hint": "人均 45 元",
                                            "business_hours_hint": "晚餐营业",
                                            "public_reason": "距离更近，预算也合适。",
                                            "source_urls": ["https://example.com/cantonese"],
                                        },
                                    ],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    provider = StepFunDinnerProvider(
        base_url="https://api.stepfun.com/v1",
        model="step-3.7-flash",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    evidence = provider.search("广州 暨南大学 附近 聚餐")

    result = provider.negotiate(
        city="广州",
        origin="暨南大学",
        topic="宿舍聚餐",
        round_count=2,
        member_preferences=[
            {"agent_name": "Alice Agent", "preferences": {"notes": "想吃川菜"}},
            {"agent_name": "Bob Agent", "preferences": {"notes": "希望近一些"}},
        ],
        previous_memory=[],
        evidence=evidence,
    )

    assert result.opening.speaker == "主持人Agent"
    assert result.agent_proposals[0].agent_name == "Alice Agent"
    assert result.agent_proposals[0].proposals[0].display_name == "校外川菜馆"
    assert result.rounds[0].turns[1].stance == "challenge"
    assert result.rounds[0].host_summary == "两位 Agent 分歧在距离和口味，两个候选都保留。"
    assert [candidate.display_name for candidate in result.candidates] == ["校外川菜馆", "粤菜小馆"]


def test_negotiate_fills_sparse_final_candidates_from_agent_proposals() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/search":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"title": "川菜馆", "url": "https://example.com/sichuan", "snippet": "人均 55 元"},
                        {"title": "火锅店", "url": "https://example.com/hotpot", "snippet": "适合聚餐"},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "opening": {"speaker": "主持人Agent", "content": "开始。"},
                                    "agent_proposals": [
                                        {
                                            "agent_name": "Alice Agent",
                                            "proposals": [
                                                {
                                                    "candidate_key": "sichuan",
                                                    "display_name": "川菜馆",
                                                    "public_reason": "预算合适",
                                                    "source_urls": ["https://example.com/sichuan"],
                                                }
                                            ],
                                        },
                                        {
                                            "agent_name": "Bob Agent",
                                            "proposals": [
                                                {
                                                    "candidate_key": "hotpot",
                                                    "display_name": "火锅店",
                                                    "public_reason": "适合聚餐",
                                                    "source_urls": ["https://example.com/hotpot"],
                                                }
                                            ],
                                        },
                                    ],
                                    "rounds": [],
                                    "coordinator_summary": "协调 Agent 首选川菜馆。",
                                    "candidates": [
                                        {
                                            "candidate_key": "sichuan",
                                            "display_name": "川菜馆",
                                            "public_reason": "预算合适",
                                            "source_urls": ["https://example.com/sichuan"],
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    provider = StepFunDinnerProvider(
        base_url="https://api.stepfun.com/v1",
        model="step-3.7-flash",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    evidence = provider.search("广州 暨南大学 聚餐")

    result = provider.negotiate(
        city="广州",
        origin="暨南大学",
        topic="宿舍聚餐",
        round_count=1,
        member_preferences=[],
        previous_memory=[],
        evidence=evidence,
    )

    assert [candidate.display_name for candidate in result.candidates] == ["川菜馆", "火锅店"]
