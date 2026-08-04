from decimal import Decimal

from app.services.ai_usage_service import AIUsageService


def test_estimate_gpt_4o_mini_cost():
    input_cost, output_cost, total = AIUsageService.estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)

    assert input_cost == Decimal("0.15")
    assert output_cost == Decimal("0.60")
    assert total == Decimal("0.75")


def test_unknown_model_has_zero_cost():
    assert AIUsageService.estimate_cost("unknown", 100, 200) == (
        Decimal("0"), Decimal("0"), Decimal("0")
    )
