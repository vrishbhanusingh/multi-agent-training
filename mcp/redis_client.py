from redis import Redis
from typing import Any, Optional
import json

class RedisClient:
    def __init__(self, host: str = "redis", port: int = 6379):
        self.redis = Redis(host=host, port=port, decode_responses=True)

    async def set_agent_state(self, agent_id: str, state: dict) -> bool:
        """Store agent state in Redis"""
        try:
            return self.redis.set(f"agent:{agent_id}:state", json.dumps(state))
        except Exception as e:
            print(f"Error setting agent state: {e}")
            return False

    async def get_agent_state(self, agent_id: str) -> Optional[dict]:
        """Retrieve agent state from Redis"""
        try:
            state = self.redis.get(f"agent:{agent_id}:state")
            return json.loads(state) if state else None
        except Exception as e:
            print(f"Error getting agent state: {e}")
            return None

    async def update_agent_memory(self, agent_id: str, memory: Any) -> bool:
        """Update agent's memory in Redis"""
        try:
            return self.redis.hset(
                f"agent:{agent_id}:memory",
                mapping={"last_update": json.dumps(memory)}
            )
        except Exception as e:
            print(f"Error updating agent memory: {e}")
            return False

    async def get_agent_memory(self, agent_id: str) -> Optional[dict]:
        """Retrieve agent's memory from Redis"""
        try:
            memory = self.redis.hgetall(f"agent:{agent_id}:memory")
            return {k: json.loads(v) for k, v in memory.items()} if memory else None
        except Exception as e:
            print(f"Error getting agent memory: {e}")
            return None 