import json
import os

import anthropic
from dotenv import load_dotenv

from agent.llm.base import BaseLLM
from agent.prompts import SYSTEM_PROMPT
from agent.tools.mysql_tools import ALL_TOOLS, TOOL_FUNCTIONS

load_dotenv()


class AnthropicLLM(BaseLLM):
    MODEL = "claude-sonnet-4-6"
    MAX_ITERATIONS = 10

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.tools = self._build_tools()
        self.history: list[dict] = []

    # BaseLLM interface
    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        return self._run_agent_loop()

    def new_session(self) -> None:
        self.history = []
        print("[AnthropicLLM] Neue Sitzung gestartet.")

    # Agent loop
    def _run_agent_loop(self) -> str:
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            try:
                response = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=4096,
                    system=[{
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    tools=self.tools,
                    messages=self.history,
                )
            except anthropic.RateLimitError as e:
                err = (
                    "⚠️ **API-Limit erreicht** — Das Claude-Kontingent ist ausgeschöpft. "
                    "Überprüfe dein Guthaben unter [console.anthropic.com](https://console.anthropic.com)."
                )
                print(f"[AnthropicLLM] Rate-Limit: {e}")
                self.history.append({"role": "assistant", "content": err})
                return err
            except anthropic.APIError as e:
                err = f"⚠️ **API-Fehler** — Anfrage konnte nicht verarbeitet werden: {e}"
                print(f"[AnthropicLLM] API-Fehler: {e}")
                self.history.append({"role": "assistant", "content": err})
                return err

            # Tool use?
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # Final text answer
                text = next(
                    (b.text for b in response.content if b.type == "text"),
                    "Entschuldigung, ich konnte keine Antwort generieren."
                )
                self.history.append({"role": "assistant", "content": response.content})
                return text

            # Append assistant turn with tool_use blocks
            self.history.append({"role": "assistant", "content": response.content})

            # Execute tools and collect results
            tool_results = []
            for block in tool_use_blocks:
                print(f"[Claude Loop {iteration}] Tool: '{block.name}' | Args: {block.input}")
                result = self._execute_tool(block.name, block.input)
                result_data = json.loads(result)
                print(f"[Claude Loop {iteration}] Ergebnis: {result_data.get('count', '?')} Datensätze")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            # Append tool results as user turn (Anthropic format)
            self.history.append({"role": "user", "content": tool_results})

        fallback = "Entschuldigung, ich konnte keine vollständige Antwort generieren."
        self.history.append({"role": "assistant", "content": fallback})
        return fallback

    # Helpers
    @staticmethod
    def _execute_tool(tool_name: str, tool_input: dict) -> str:
        if tool_name not in TOOL_FUNCTIONS:
            return json.dumps({"error": f"Unbekanntes Tool: {tool_name}"})
        try:
            return TOOL_FUNCTIONS[tool_name](**tool_input)
        except Exception as e:
            return json.dumps({"error": f"Tool-Fehler bei {tool_name}: {str(e)}"})

    @staticmethod
    def _build_tools() -> list[dict]:
        # ALL_TOOLS ist bereits im Anthropic-Format (name, description, input_schema)
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in ALL_TOOLS
        ]
