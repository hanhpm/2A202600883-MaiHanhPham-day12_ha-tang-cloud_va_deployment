"""Monthly LLM budget guard with Redis storage and in-memory fallback."""
import time

from fastapi import HTTPException

from app.config import settings

try:
    import redis
except ImportError:  # pragma: no cover - exercised only before dependencies are installed
    redis = None

PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006


class CostGuard:
    def __init__(self):
        self._redis = None
        self._memory_costs: dict[str, float] = {}
        if redis and settings.redis_url:
            try:
                self._redis = redis.Redis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                    decode_responses=True,
                )
                self._redis.ping()
            except redis.RedisError:
                self._redis = None

    def _month_key(self, user_id: str) -> str:
        return f"cost:{time.strftime('%Y-%m')}:{user_id}"

    def check_monthly_budget(self, user_id: str) -> None:
        spent = self._get_cost(user_id)
        if spent >= settings.monthly_budget_usd:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "spent_usd": round(spent, 6),
                    "budget_usd": settings.monthly_budget_usd,
                },
            )

    def record_usage(self, user_id: str, input_tokens: int, output_tokens: int) -> dict:
        cost = (
            input_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS
            + output_tokens / 1000 * PRICE_PER_1K_OUTPUT_TOKENS
        )
        total = self._add_cost(user_id, cost)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "month_spent_usd": round(total, 6),
            "monthly_budget_usd": settings.monthly_budget_usd,
        }

    def _get_cost(self, user_id: str) -> float:
        key = self._month_key(user_id)
        if self._redis:
            try:
                return float(self._redis.get(key) or 0.0)
            except redis.RedisError:
                self._redis = None
        return self._memory_costs.get(key, 0.0)

    def _add_cost(self, user_id: str, cost: float) -> float:
        key = self._month_key(user_id)
        if self._redis:
            try:
                total = float(self._redis.incrbyfloat(key, cost))
                self._redis.expire(key, 60 * 60 * 24 * 40)
                return total
            except redis.RedisError:
                self._redis = None
        self._memory_costs[key] = self._memory_costs.get(key, 0.0) + cost
        return self._memory_costs[key]


cost_guard = CostGuard()
