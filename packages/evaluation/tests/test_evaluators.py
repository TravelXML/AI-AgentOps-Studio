from evaluation.evaluators import EvalContext, run_evaluator


def _ctx(**kwargs) -> EvalContext:
    defaults = dict(
        actual_output=None, expected_output=None, total_cost_usd=0.0, duration_ms=None, run_error=None
    )
    defaults.update(kwargs)
    return EvalContext(**defaults)


async def test_exact_match_pass_and_fail():
    ok = await run_evaluator(
        "exact_match", {}, _ctx(actual_output="hi", expected_output="hi"), None, "default"
    )
    bad = await run_evaluator(
        "exact_match", {}, _ctx(actual_output="hi", expected_output="bye"), None, "default"
    )
    assert ok.passed is True
    assert bad.passed is False


async def test_contains_checks_substring():
    ctx = _ctx(actual_output="The answer is 42.")
    result = await run_evaluator("contains", {"value": "42"}, ctx, None, "default")
    assert result.passed is True

    miss = await run_evaluator("contains", {"value": "99"}, ctx, None, "default")
    assert miss.passed is False


async def test_regex_matches_pattern():
    ctx = _ctx(actual_output="order-12345")
    result = await run_evaluator("regex", {"pattern": r"order-\d+"}, ctx, None, "default")
    assert result.passed is True


async def test_regex_invalid_pattern_fails_gracefully():
    ctx = _ctx(actual_output="anything")
    result = await run_evaluator("regex", {"pattern": "("}, ctx, None, "default")
    assert result.passed is False
    assert "invalid pattern" in result.detail


async def test_schema_requires_fields():
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    ok = await run_evaluator("schema", {"schema": schema}, _ctx(actual_output={"name": "a"}), None, "default")
    missing = await run_evaluator("schema", {"schema": schema}, _ctx(actual_output={}), None, "default")
    wrong_type = await run_evaluator(
        "schema", {"schema": schema}, _ctx(actual_output={"name": 5}), None, "default"
    )
    assert ok.passed is True
    assert missing.passed is False
    assert wrong_type.passed is False


async def test_latency_threshold():
    within = await run_evaluator("latency", {"max_ms": 1000}, _ctx(duration_ms=500), None, "default")
    over = await run_evaluator("latency", {"max_ms": 1000}, _ctx(duration_ms=1500), None, "default")
    assert within.passed is True
    assert over.passed is False


async def test_cost_threshold():
    within = await run_evaluator("cost", {"max_usd": 0.01}, _ctx(total_cost_usd=0.005), None, "default")
    over = await run_evaluator("cost", {"max_usd": 0.01}, _ctx(total_cost_usd=0.02), None, "default")
    assert within.passed is True
    assert over.passed is False


class _StubGateway:
    def __init__(self, verdict: str) -> None:
        self._verdict = verdict

    async def complete(self, model_id, messages, *, temperature=None, max_tokens=None):
        from model_gateway import ModelResponse, TokenUsage

        return ModelResponse(
            content=self._verdict,
            provider="mock",
            model=model_id,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            estimated_cost_usd=0.0,
            latency_ms=1.0,
        )


async def test_llm_judge_pass_and_fail():
    ctx = _ctx(actual_output="Paris", expected_output="Paris")
    passed = await run_evaluator("llm_judge", {"criteria": "matches"}, ctx, _StubGateway("PASS"), "default")
    failed = await run_evaluator("llm_judge", {"criteria": "matches"}, ctx, _StubGateway("FAIL"), "default")
    assert passed.passed is True
    assert failed.passed is False


async def test_unknown_evaluator_type_fails_honestly():
    result = await run_evaluator("not_a_real_evaluator", {}, _ctx(), None, "default")
    assert result.passed is False
    assert "unknown evaluator" in result.detail
