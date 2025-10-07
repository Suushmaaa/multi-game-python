from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import uuid
import sys
import os
from datetime import datetime

# Add the backend directory to the path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except (ImportError, TypeError) as e:
    print(f"LangChain not available: {e}")
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None

class BaseAgent(ABC):
    def __init__(self, agent_name: str, model_name: str = "gpt-3.5-turbo"):
        self.agent_id = f"{agent_name}_{str(uuid.uuid4())[:8]}"
        self.agent_name = agent_name
        self.model_name = model_name
        self.logger = logging.getLogger(f"agents.{agent_name}")

        self.conversation_history: List[Dict[str, str]] = []
        self.created_at = datetime.now()

        # Initialize LangChain LLM if available and API key is set
        self.llm = None
        if LANGCHAIN_AVAILABLE and settings.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    model_name=self.model_name,
                    openai_api_key=settings.openai_api_key,
                    temperature=0.7
                )
                self.logger.info(f"Initialized LangChain LLM for {agent_name}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM for {agent_name}: {e}")
        else:
            self.logger.info(f"Using mock mode for {agent_name} (no LLM available)")

    def add_system_message(self, content: str):
        """Add a system message to conversation history"""
        self.conversation_history.append({"role": "system", "content": content})

    def add_human_message(self, content: str):
        """Add a human message to conversation history"""
        self.conversation_history.append({"role": "user", "content": content})

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the main functionality of the agent"""
        pass

    def get_agent_info(self) -> Dict[str, Any]:
        """Get basic agent information"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "model_name": self.model_name,
            "created_at": self.created_at.isoformat(),
            "conversation_length": len(self.conversation_history)
        }
