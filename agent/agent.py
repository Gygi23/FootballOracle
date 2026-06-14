from __future__ import annotations
import os
from agent.llm.base import BaseLLM


def _create_llm() -> BaseLLM:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "claude":
        from agent.llm.anthropic import AnthropicLLM
        return AnthropicLLM()
    elif provider == "ollama":
        from agent.llm.ollama import OllamaLLM
        return OllamaLLM()
    else:
        from agent.llm.gemini import GeminiLLM
        return GeminiLLM()


class FootballAIAgent:
    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or _create_llm()

    def chat(self, user_message: str) -> str:
        print(f"\n{'='*60}")
        print(f"USER: {user_message}")
        print(f"{'='*60}")
        response = self.llm.chat(user_message)
        print(f"\nASSISTANT: {response}")
        return response
 
    def new_session(self) -> None:
        self.llm.new_session()
