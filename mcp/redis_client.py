from redis import Redis
from typing import Any, Optional, Dict, List, Tuple
import json
import time

class RedisClient:
    def __init__(self, host: str = "redis", port: int = 6379):
        self.redis = Redis(host=host, port=port, decode_responses=True)
        
    # ===== Agent State Methods =====
    
    async def set_agent_state(self, agent_id: str, state: dict, ttl: int = 3600) -> bool:
        """
        Store agent state in Redis with optional TTL.
        
        Args:
            agent_id: Unique identifier for the agent
            state: Dictionary of agent state data
            ttl: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            bool: Success or failure
        """
        try:
            # Always add timestamp to state
            state["last_updated"] = time.time()
            
            # Store state as JSON with expiration
            key = f"agent:{agent_id}:state"
            success = self.redis.set(key, json.dumps(state))
            
            # Set expiration if TTL is provided
            if ttl > 0:
                self.redis.expire(key, ttl)
                
            return success
        except Exception as e:
            print(f"Error setting agent state: {e}")
            return False

    async def get_agent_state(self, agent_id: str) -> Optional[dict]:
        """
        Retrieve agent state from Redis.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Optional[dict]: Agent state or None if not found
        """
        try:
            state = self.redis.get(f"agent:{agent_id}:state")
            return json.loads(state) if state else None
        except Exception as e:
            print(f"Error getting agent state: {e}")
            return None
            
    async def delete_agent_state(self, agent_id: str) -> bool:
        """
        Delete agent state from Redis.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            bool: Success or failure
        """
        try:
            return bool(self.redis.delete(f"agent:{agent_id}:state"))
        except Exception as e:
            print(f"Error deleting agent state: {e}")
            return False
    
    # ===== Agent Memory Methods =====
    
    async def add_memory_entry(self, agent_id: str, entry_type: str, data: Dict) -> bool:
        """
        Add a new memory entry to an agent's memory.
        
        Args:
            agent_id: Unique identifier for the agent
            entry_type: Type of memory entry (e.g., 'message', 'observation', 'interaction')
            data: Memory entry data
            
        Returns:
            bool: Success or failure
        """
        try:
            # Generate a unique timestamp-based ID for the entry
            timestamp = time.time()
            entry_id = f"{timestamp:.6f}"
            
            # Add metadata to the entry
            entry = {
                "id": entry_id,
                "type": entry_type,
                "timestamp": timestamp,
                "data": data
            }
            
            # Store in sorted set with score as timestamp for chronological retrieval
            memory_key = f"agent:{agent_id}:memory:{entry_type}"
            self.redis.zadd(memory_key, {json.dumps(entry): timestamp})
            
            # Also maintain a list of all memory types for this agent
            memory_types_key = f"agent:{agent_id}:memory:types"
            self.redis.sadd(memory_types_key, entry_type)
            
            return True
        except Exception as e:
            print(f"Error adding memory entry: {e}")
            return False
            
    async def get_memory_entries(self, agent_id: str, entry_type: str, limit: int = 10, 
                                reverse: bool = True) -> List[Dict]:
        """
        Get memory entries of a specific type, sorted by timestamp.
        
        Args:
            agent_id: Unique identifier for the agent
            entry_type: Type of memory to retrieve
            limit: Maximum number of entries to retrieve
            reverse: If True, return newest entries first
            
        Returns:
            List[Dict]: List of memory entries
        """
        try:
            memory_key = f"agent:{agent_id}:memory:{entry_type}"
            
            if reverse:
                # Get newest entries (highest scores) first
                entries_json = self.redis.zrevrange(memory_key, 0, limit - 1)
            else:
                # Get oldest entries (lowest scores) first
                entries_json = self.redis.zrange(memory_key, 0, limit - 1)
                
            return [json.loads(entry) for entry in entries_json]
        except Exception as e:
            print(f"Error getting memory entries: {e}")
            return []
            
    async def get_all_memory(self, agent_id: str, limit: int = 50) -> Dict[str, List[Dict]]:
        """
        Get all memory entries for an agent, organized by type.
        
        Args:
            agent_id: Unique identifier for the agent
            limit: Maximum entries per type
            
        Returns:
            Dict[str, List[Dict]]: Dictionary of memory entries by type
        """
        try:
            # Get all memory types for this agent
            memory_types_key = f"agent:{agent_id}:memory:types"
            memory_types = self.redis.smembers(memory_types_key)
            
            # Get entries for each type
            result = {}
            for entry_type in memory_types:
                result[entry_type] = await self.get_memory_entries(agent_id, entry_type, limit)
                
            return result
        except Exception as e:
            print(f"Error getting all memory: {e}")
            return {}
            
    async def clear_memory(self, agent_id: str, entry_type: Optional[str] = None) -> bool:
        """
        Clear memory entries for an agent, optionally filtering by type.
        
        Args:
            agent_id: Unique identifier for the agent
            entry_type: Optional specific type to clear (None for all)
            
        Returns:
            bool: Success or failure
        """
        try:
            if entry_type:
                # Clear specific memory type
                memory_key = f"agent:{agent_id}:memory:{entry_type}"
                return bool(self.redis.delete(memory_key))
            else:
                # Clear all memory types
                memory_types_key = f"agent:{agent_id}:memory:types"
                memory_types = self.redis.smembers(memory_types_key)
                
                pipeline = self.redis.pipeline()
                for entry_type in memory_types:
                    memory_key = f"agent:{agent_id}:memory:{entry_type}"
                    pipeline.delete(memory_key)
                pipeline.delete(memory_types_key)
                pipeline.execute()
                
                return True
        except Exception as e:
            print(f"Error clearing memory: {e}")
            return False
            
    # ===== Deprecated Methods (Maintained for Backward Compatibility) =====
    
    async def update_agent_memory(self, agent_id: str, memory: Any) -> bool:
        """
        Update agent's memory in Redis (deprecated, use add_memory_entry instead).
        """
        try:
            return await self.add_memory_entry(agent_id, "legacy", memory)
        except Exception as e:
            print(f"Error updating agent memory: {e}")
            return False

    async def get_agent_memory(self, agent_id: str) -> Optional[dict]:
        """
        Retrieve agent's memory from Redis (deprecated, use get_all_memory instead).
        """
        try:
            legacy_entries = await self.get_memory_entries(agent_id, "legacy", limit=1)
            if legacy_entries:
                return legacy_entries[0]["data"]
            
            # Fall back to old format if needed
            memory = self.redis.hgetall(f"agent:{agent_id}:memory")
            return {k: json.loads(v) for k, v in memory.items()} if memory else None
        except Exception as e:
            print(f"Error getting agent memory: {e}")
            return None 