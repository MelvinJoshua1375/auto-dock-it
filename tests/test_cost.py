from autodock.llm import estimate_cost_usd


def test_known_model_costs():
    cost = estimate_cost_usd("gemini-2.5-flash", input_tokens=1_000_000, output_tokens=0)
    assert abs(cost - 0.075) < 1e-9


def test_output_priced_higher():
    only_in = estimate_cost_usd("llama-3.3-70b-versatile", 1_000_000, 0)
    only_out = estimate_cost_usd("llama-3.3-70b-versatile", 0, 1_000_000)
    assert only_out > only_in


def test_unknown_model_returns_zero():
    assert estimate_cost_usd("some-future-model", 1_000_000, 1_000_000) == 0.0


def test_small_run_yields_small_cost():
    cost = estimate_cost_usd("gemini-2.5-flash", input_tokens=5_000, output_tokens=2_000)
    assert 0 < cost < 0.01
