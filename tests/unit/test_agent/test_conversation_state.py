"""
Unit tests for conversation state management

Tests the core business logic for managing conversation state,
including history tracking, context preservation, and multi-turn
reasoning support.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
import json


class TestConversationStateLogic:
    """Test cases for conversation state management business logic"""

    def test_conversation_initialization(self):
        """Test initialization of new conversation state"""
        # Arrange
        class ConversationState:
            def __init__(self, conversation_id=None, user_id=None):
                self.conversation_id = conversation_id or f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.user_id = user_id
                self.created_at = datetime.now()
                self.updated_at = datetime.now()
                self.turns = []
                self.context = {}
                self.metadata = {}
                self.is_active = True
            
            def to_dict(self):
                return {
                    "conversation_id": self.conversation_id,
                    "user_id": self.user_id,
                    "created_at": self.created_at.isoformat(),
                    "updated_at": self.updated_at.isoformat(),
                    "turns": self.turns,
                    "context": self.context,
                    "metadata": self.metadata,
                    "is_active": self.is_active
                }
        
        # Act
        conv1 = ConversationState(user_id="user123")
        conv2 = ConversationState(conversation_id="custom_conv_id", user_id="user456")
        
        # Assert
        assert conv1.conversation_id.startswith("conv_")
        assert conv1.user_id == "user123"
        assert conv1.is_active is True
        assert len(conv1.turns) == 0
        assert isinstance(conv1.created_at, datetime)
        
        assert conv2.conversation_id == "custom_conv_id"
        assert conv2.user_id == "user456"
        
        # Test serialization
        conv_dict = conv1.to_dict()
        assert "conversation_id" in conv_dict
        assert "created_at" in conv_dict
        assert isinstance(conv_dict["turns"], list)

    def test_turn_management(self):
        """Test adding and managing conversation turns"""
        # Arrange
        class ConversationTurn:
            def __init__(self, role, content, timestamp=None, metadata=None):
                self.role = role  # "user" or "assistant"
                self.content = content
                self.timestamp = timestamp or datetime.now()
                self.metadata = metadata or {}
            
            def to_dict(self):
                return {
                    "role": self.role,
                    "content": self.content,
                    "timestamp": self.timestamp.isoformat(),
                    "metadata": self.metadata
                }
        
        class ConversationManager:
            def __init__(self):
                self.conversations = {}
            
            def add_turn(self, conversation_id, role, content, metadata=None):
                if conversation_id not in self.conversations:
                    return False, "Conversation not found"
                
                turn = ConversationTurn(role, content, metadata=metadata)
                self.conversations[conversation_id].turns.append(turn)
                self.conversations[conversation_id].updated_at = datetime.now()
                
                return True, turn
            
            def get_recent_turns(self, conversation_id, limit=10):
                if conversation_id not in self.conversations:
                    return []
                
                turns = self.conversations[conversation_id].turns
                return turns[-limit:] if len(turns) > limit else turns
            
            def get_turn_count(self, conversation_id):
                if conversation_id not in self.conversations:
                    return 0
                return len(self.conversations[conversation_id].turns)
        
        # Act
        manager = ConversationManager()
        conv_id = "test_conv"
        
        # Create conversation
        manager.conversations[conv_id] = ConversationState(conv_id)
        
        # Add turns
        success1, turn1 = manager.add_turn(conv_id, "user", "Hello, what is 2+2?")
        success2, turn2 = manager.add_turn(conv_id, "assistant", "2+2 equals 4.")
        success3, turn3 = manager.add_turn(conv_id, "user", "What about 3+3?")
        
        # Assert
        assert success1 is True
        assert turn1.role == "user"
        assert turn1.content == "Hello, what is 2+2?"
        
        assert manager.get_turn_count(conv_id) == 3
        
        recent_turns = manager.get_recent_turns(conv_id, limit=2)
        assert len(recent_turns) == 2
        assert recent_turns[0].role == "assistant"
        assert recent_turns[1].role == "user"

    def test_context_preservation(self):
        """Test preservation and retrieval of conversation context"""
        # Arrange
        class ContextManager:
            def __init__(self):
                self.contexts = {}
            
            def set_context(self, conversation_id, key, value, ttl_minutes=None):
                """Set context value with optional TTL"""
                if conversation_id not in self.contexts:
                    self.contexts[conversation_id] = {}
                
                context_entry = {
                    "value": value,
                    "created_at": datetime.now(),
                    "ttl_minutes": ttl_minutes
                }
                
                self.contexts[conversation_id][key] = context_entry
            
            def get_context(self, conversation_id, key, default=None):
                """Get context value, respecting TTL"""
                if conversation_id not in self.contexts:
                    return default
                
                if key not in self.contexts[conversation_id]:
                    return default
                
                entry = self.contexts[conversation_id][key]
                
                # Check TTL
                if entry["ttl_minutes"]:
                    age = datetime.now() - entry["created_at"]
                    if age > timedelta(minutes=entry["ttl_minutes"]):
                        # Expired
                        del self.contexts[conversation_id][key]
                        return default
                
                return entry["value"]
            
            def update_context(self, conversation_id, updates):
                """Update multiple context values"""
                for key, value in updates.items():
                    self.set_context(conversation_id, key, value)
            
            def clear_context(self, conversation_id, keys=None):
                """Clear specific keys or entire context"""
                if conversation_id not in self.contexts:
                    return
                
                if keys is None:
                    # Clear all context
                    self.contexts[conversation_id] = {}
                else:
                    # Clear specific keys
                    for key in keys:
                        self.contexts[conversation_id].pop(key, None)
            
            def get_all_context(self, conversation_id):
                """Get all context for conversation"""
                if conversation_id not in self.contexts:
                    return {}
                
                # Filter out expired entries
                valid_context = {}
                for key, entry in self.contexts[conversation_id].items():
                    if entry["ttl_minutes"]:
                        age = datetime.now() - entry["created_at"]
                        if age <= timedelta(minutes=entry["ttl_minutes"]):
                            valid_context[key] = entry["value"]
                    else:
                        valid_context[key] = entry["value"]
                
                return valid_context
        
        # Act
        context_manager = ContextManager()
        conv_id = "test_conv"
        
        # Set various context values
        context_manager.set_context(conv_id, "user_name", "Alice")
        context_manager.set_context(conv_id, "topic", "mathematics")
        context_manager.set_context(conv_id, "temp_calculation", "2+2=4", ttl_minutes=1)
        
        # Assert
        assert context_manager.get_context(conv_id, "user_name") == "Alice"
        assert context_manager.get_context(conv_id, "topic") == "mathematics"
        assert context_manager.get_context(conv_id, "temp_calculation") == "2+2=4"
        assert context_manager.get_context(conv_id, "nonexistent", "default") == "default"
        
        # Test bulk updates
        context_manager.update_context(conv_id, {
            "calculation_count": 1,
            "last_operation": "addition"
        })
        
        all_context = context_manager.get_all_context(conv_id)
        assert "calculation_count" in all_context
        assert "last_operation" in all_context
        assert len(all_context) == 5
        
        # Test clearing specific keys
        context_manager.clear_context(conv_id, ["temp_calculation"])
        assert context_manager.get_context(conv_id, "temp_calculation") is None
        assert context_manager.get_context(conv_id, "user_name") == "Alice"

    def test_multi_turn_reasoning_state(self):
        """Test state management for multi-turn reasoning"""
        # Arrange
        class ReasoningStateManager:
            def __init__(self):
                self.reasoning_states = {}
            
            def start_reasoning_session(self, conversation_id, question, reasoning_type="sequential"):
                """Start a new reasoning session"""
                session_id = f"{conversation_id}_reasoning_{datetime.now().strftime('%H%M%S')}"
                
                self.reasoning_states[session_id] = {
                    "conversation_id": conversation_id,
                    "original_question": question,
                    "reasoning_type": reasoning_type,
                    "status": "active",
                    "steps": [],
                    "intermediate_results": {},
                    "final_answer": None,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                return session_id
            
            def add_reasoning_step(self, session_id, step_type, content, tool_result=None):
                """Add a step to reasoning session"""
                if session_id not in self.reasoning_states:
                    return False
                
                step = {
                    "step_number": len(self.reasoning_states[session_id]["steps"]) + 1,
                    "step_type": step_type,  # "think", "act", "observe"
                    "content": content,
                    "tool_result": tool_result,
                    "timestamp": datetime.now()
                }
                
                self.reasoning_states[session_id]["steps"].append(step)
                self.reasoning_states[session_id]["updated_at"] = datetime.now()
                
                return True
            
            def set_intermediate_result(self, session_id, key, value):
                """Store intermediate result for later use"""
                if session_id not in self.reasoning_states:
                    return False
                
                self.reasoning_states[session_id]["intermediate_results"][key] = value
                return True
            
            def get_intermediate_result(self, session_id, key):
                """Retrieve intermediate result"""
                if session_id not in self.reasoning_states:
                    return None
                
                return self.reasoning_states[session_id]["intermediate_results"].get(key)
            
            def complete_reasoning_session(self, session_id, final_answer):
                """Mark reasoning session as complete"""
                if session_id not in self.reasoning_states:
                    return False
                
                self.reasoning_states[session_id]["final_answer"] = final_answer
                self.reasoning_states[session_id]["status"] = "completed"
                self.reasoning_states[session_id]["updated_at"] = datetime.now()
                
                return True
            
            def get_reasoning_summary(self, session_id):
                """Get summary of reasoning session"""
                if session_id not in self.reasoning_states:
                    return None
                
                state = self.reasoning_states[session_id]
                return {
                    "original_question": state["original_question"],
                    "step_count": len(state["steps"]),
                    "status": state["status"],
                    "final_answer": state["final_answer"],
                    "reasoning_chain": [step["content"] for step in state["steps"] if step["step_type"] == "think"]
                }
        
        # Act
        reasoning_manager = ReasoningStateManager()
        conv_id = "test_conv"
        
        # Start reasoning session
        session_id = reasoning_manager.start_reasoning_session(
            conv_id, 
            "What is the population of the capital of France?"
        )
        
        # Add reasoning steps
        reasoning_manager.add_reasoning_step(session_id, "think", "I need to find the capital first")
        reasoning_manager.add_reasoning_step(session_id, "act", "search for capital of France", "Paris")
        reasoning_manager.set_intermediate_result(session_id, "capital", "Paris")
        
        reasoning_manager.add_reasoning_step(session_id, "observe", "Found that Paris is the capital")
        reasoning_manager.add_reasoning_step(session_id, "think", "Now I need to find Paris population")
        reasoning_manager.add_reasoning_step(session_id, "act", "search for Paris population", "2.1 million")
        
        reasoning_manager.complete_reasoning_session(session_id, "The population of Paris is approximately 2.1 million")
        
        # Assert
        assert session_id.startswith(f"{conv_id}_reasoning_")
        
        capital = reasoning_manager.get_intermediate_result(session_id, "capital")
        assert capital == "Paris"
        
        summary = reasoning_manager.get_reasoning_summary(session_id)
        assert summary["original_question"] == "What is the population of the capital of France?"
        assert summary["step_count"] == 5
        assert summary["status"] == "completed"
        assert "2.1 million" in summary["final_answer"]
        assert len(summary["reasoning_chain"]) == 2  # Two "think" steps

    def test_conversation_memory_management(self):
        """Test memory management for long conversations"""
        # Arrange
        class ConversationMemoryManager:
            def __init__(self, max_turns=100, max_context_age_hours=24):
                self.max_turns = max_turns
                self.max_context_age_hours = max_context_age_hours
                self.conversations = {}
            
            def add_conversation_turn(self, conversation_id, role, content, metadata=None):
                """Add turn with automatic memory management"""
                if conversation_id not in self.conversations:
                    self.conversations[conversation_id] = {
                        "turns": [],
                        "context": {},
                        "created_at": datetime.now()
                    }
                
                turn = {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now(),
                    "metadata": metadata or {}
                }
                
                self.conversations[conversation_id]["turns"].append(turn)
                
                # Apply memory management
                self._manage_memory(conversation_id)
            
            def _manage_memory(self, conversation_id):
                """Apply memory management policies"""
                conv = self.conversations[conversation_id]
                
                # Limit turn count
                if len(conv["turns"]) > self.max_turns:
                    # Keep recent turns and important summary turns
                    turns_to_keep = self.max_turns // 2
                    important_turns = self._identify_important_turns(conv["turns"])
                    recent_turns = conv["turns"][-turns_to_keep:]
                    
                    # Combine important and recent turns, avoiding duplicates
                    kept_turns = []
                    seen_indices = set()
                    
                    # Add important turns first
                    for turn_index, turn in important_turns:
                        if turn_index not in seen_indices:
                            kept_turns.append(turn)
                            seen_indices.add(turn_index)
                    
                    # Add recent turns
                    for i, turn in enumerate(recent_turns):
                        original_index = len(conv["turns"]) - len(recent_turns) + i
                        if original_index not in seen_indices:
                            kept_turns.append(turn)
                    
                    conv["turns"] = kept_turns[-self.max_turns:]  # Final limit
                
                # Clean old context
                self._clean_old_context(conversation_id)
            
            def _identify_important_turns(self, turns):
                """Identify important turns to preserve"""
                important = []
                
                for i, turn in enumerate(turns):
                    # Keep turns with high information content
                    if (len(turn["content"]) > 100 or 
                        any(keyword in turn["content"].lower() for keyword in ["calculate", "result", "answer", "conclusion"])):
                        important.append((i, turn))
                
                return important[:10]  # Limit important turns
            
            def _clean_old_context(self, conversation_id):
                """Remove old context entries"""
                if conversation_id not in self.conversations:
                    return
                
                cutoff_time = datetime.now() - timedelta(hours=self.max_context_age_hours)
                context = self.conversations[conversation_id]["context"]
                
                keys_to_remove = []
                for key, entry in context.items():
                    if isinstance(entry, dict) and "timestamp" in entry:
                        if entry["timestamp"] < cutoff_time:
                            keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del context[key]
            
            def get_conversation_summary(self, conversation_id):
                """Get summary of conversation state"""
                if conversation_id not in self.conversations:
                    return None
                
                conv = self.conversations[conversation_id]
                return {
                    "turn_count": len(conv["turns"]),
                    "context_keys": list(conv["context"].keys()),
                    "age_hours": (datetime.now() - conv["created_at"]).total_seconds() / 3600,
                    "last_activity": conv["turns"][-1]["timestamp"] if conv["turns"] else None
                }
        
        # Act
        memory_manager = ConversationMemoryManager(max_turns=5, max_context_age_hours=1)
        conv_id = "test_memory_conv"
        
        # Add many turns to test memory management
        for i in range(10):
            memory_manager.add_conversation_turn(
                conv_id, 
                "user" if i % 2 == 0 else "assistant",
                f"Turn {i}: {'Important calculation result' if i == 5 else 'Regular content'}"
            )
        
        # Assert
        summary = memory_manager.get_conversation_summary(conv_id)
        assert summary["turn_count"] <= 5  # Should be limited
        
        # Check that important turns are preserved
        turns = memory_manager.conversations[conv_id]["turns"]
        important_preserved = any("Important calculation" in turn["content"] for turn in turns)
        assert important_preserved, "Important turns should be preserved"

    def test_conversation_state_persistence(self):
        """Test serialization and deserialization of conversation state"""
        # Arrange
        class ConversationStatePersistence:
            def __init__(self):
                pass
            
            def serialize_conversation(self, conversation_state):
                """Serialize conversation state to JSON-compatible format"""
                def datetime_serializer(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                return json.dumps(conversation_state, default=datetime_serializer, indent=2)
            
            def deserialize_conversation(self, serialized_data):
                """Deserialize conversation state from JSON"""
                def datetime_deserializer(data):
                    """Convert ISO datetime strings back to datetime objects"""
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, str) and self._is_iso_datetime(value):
                                data[key] = datetime.fromisoformat(value)
                            elif isinstance(value, (dict, list)):
                                data[key] = datetime_deserializer(value)
                    elif isinstance(data, list):
                        for i, item in enumerate(data):
                            data[i] = datetime_deserializer(item)
                    
                    return data
                
                parsed_data = json.loads(serialized_data)
                return datetime_deserializer(parsed_data)
            
            def _is_iso_datetime(self, value):
                """Check if string is ISO datetime format"""
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return True
                except (ValueError, AttributeError):
                    return False
        
        # Create sample conversation state
        conversation_state = {
            "conversation_id": "test_conv_123",
            "user_id": "user456",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "turns": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now(),
                    "metadata": {}
                },
                {
                    "role": "assistant", 
                    "content": "Hi there!",
                    "timestamp": datetime.now(),
                    "metadata": {"confidence": 0.9}
                }
            ],
            "context": {
                "user_preference": "detailed_answers",
                "topic": "general"
            },
            "metadata": {
                "platform": "web",
                "session_start": datetime.now()
            }
        }
        
        # Act
        persistence = ConversationStatePersistence()
        
        # Serialize
        serialized = persistence.serialize_conversation(conversation_state)
        assert isinstance(serialized, str)
        assert "test_conv_123" in serialized
        
        # Deserialize
        deserialized = persistence.deserialize_conversation(serialized)
        
        # Assert
        assert deserialized["conversation_id"] == "test_conv_123"
        assert deserialized["user_id"] == "user456"
        assert isinstance(deserialized["created_at"], datetime)
        assert len(deserialized["turns"]) == 2
        assert deserialized["turns"][0]["role"] == "user"
        assert isinstance(deserialized["turns"][0]["timestamp"], datetime)
        assert deserialized["context"]["topic"] == "general"
        assert deserialized["metadata"]["platform"] == "web"