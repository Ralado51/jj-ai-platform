from uuid import uuid4

from app.services.analytics_service import AnalyticsService


class FakeBenchmarkRepository:
    def summary(self, *, user_id):
        assert user_id is not None
        return {
            "total_runs": 3,
            "total_results": 6,
            "success_rate": 83.33,
            "top_model": "gemma3:4b",
            "models": [
                {
                    "model": "gemma3:4b",
                    "executions": 3,
                    "average_score": 8.9,
                    "average_duration_ms": 3100,
                    "estimated_tokens": 2100,
                }
            ],
            "winners": [{"model": "gemma3:4b", "wins": 2}],
        }


def test_analytics_summary_returns_model_ranking() -> None:
    service = AnalyticsService(FakeBenchmarkRepository())

    result = service.summary(user_id=uuid4())

    assert result.total_runs == 3
    assert result.success_rate == 83.33
    assert result.top_model == "gemma3:4b"
    assert result.models[0].average_score == 8.9
    assert result.winners[0].wins == 2
