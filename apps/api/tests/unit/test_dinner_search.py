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
