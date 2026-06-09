import json

from openai import OpenAI

from agent.llm.base import BaseLLM
from agent.prompts import SYSTEM_PROMPT
from agent.tools.mysql_tools import ALL_TOOLS, TOOL_FUNCTIONS


class OllamaLLM(BaseLLM):
    MODEL = "llama3.2"
    MAX_ITERATIONS = 10
    BASE_URL = "http://localhost:11434/v1"

    def __init__(self):
        self.client = OpenAI(base_url=self.BASE_URL, api_key="ollama")
        self.tools = self._build_tools()
        self.history: list[dict] = []

    # BaseLLM interface
    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        return self.run_agent_loop()

    def new_session(self) -> None:
        self.history = []
        print("[OllamaLLM] Neue Sitzung gestartet.")

    # Agent loop
    def run_agent_loop(self) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                    tools=self.tools,
                )
            except Exception as e:
                err = f"⚠️ **Ollama-Fehler** — {e}"
                print(f"[OllamaLLM] Fehler: {e}")
                self.history.append({"role": "assistant", "content": err})
                return err

            msg = response.choices[0].message

            # Tool calls?
            if msg.tool_calls:
                # Append assistant message with tool_calls
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                # Execute each tool and append results
                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    print(f"[Ollama Loop {iteration}] Tool: '{name}' | Args: {args}")
                    result = self._execute_tool(name, args)
                    result_data = json.loads(result)
                    print(f"[Ollama Loop {iteration}] Ergebnis: {result_data.get('count', '?')} Datensätze")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                # Next iteration with tool results
                continue

            # Final text answer
            text = msg.content or "Entschuldigung, ich konnte keine Antwort generieren."
            self.history.append({"role": "assistant", "content": text})
            return text

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
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in ALL_TOOLS
        ]
