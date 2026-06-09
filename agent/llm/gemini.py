import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from agent.llm.base import BaseLLM
from agent.prompts import SYSTEM_PROMPT
from agent.tools.mysql_tools import ALL_TOOLS, TOOL_FUNCTIONS

load_dotenv()

class GeminiLLM(BaseLLM):
    MODEL = "gemini-2.0-flash"
    MAX_ITERATIONS = 10

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.tools = self.build_tools()
        self.chat_session = self.new_chat()

    # BaseLLM interface
    def chat(self, user_message: str) -> str:
        return self.run_agent_loop(user_message)

    def new_session(self) -> None:
        self.chat_session = self.new_chat()
        print("[GeminiLLM] Neue Sitzung gestartet.")

    # Agent loop
    def run_agent_loop(self, user_message: str) -> str:
        try:
            response = self.chat_session.send_message(user_message)
        except ClientError as e:
            return self._handle_api_error(e)

        iteration = 0

        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            candidate = response.candidates[0]

            if not candidate.content or not candidate.content.parts:
                return self.extract_text(response)

            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if part.function_call is not None
            ]

            # final answer - no tool calling
            if not function_calls:
                return self.extract_text(response)

            # tool-calls
            tool_response = []
            for fc in function_calls:
                print(f"[Gemini Loop {iteration}] Tool: '{fc.name}' | Args: {dict(fc.args)}")
                result = self.execute_tool(fc.name, dict(fc.args))
                print("RAW:", result[:300])
                result_data = json.loads(result)
                print(f"[Gemini Loop {iteration}] Ergebnis: {result_data.get('count', '?')} Datensätze")

                tool_response.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response=result_data,
                        )
                    )
                )

            try:
                response = self.chat_session.send_message(tool_response)
            except ClientError as e:
                return self._handle_api_error(e)

        return "Entschuldigung, ich konnte keine vollständige Antwort generieren."

    @staticmethod
    def _handle_api_error(e: ClientError) -> str:
        if e.status_code == 429:
            print(f"[GeminiLLM] Rate-Limit erreicht: {e}")
            return (
                "⚠️ **API-Limit erreicht** — Das Gemini-Kontingent für heute ist ausgeschöpft. "
                "Bitte warte einige Stunden oder überprüfe dein API-Kontingent unter "
                "[ai.dev/rate-limit](https://ai.dev/rate-limit)."
            )
        print(f"[GeminiLLM] API-Fehler {e.status_code}: {e}")
        return f"⚠️ **API-Fehler** — Anfrage konnte nicht verarbeitet werden (Status {e.status_code})."

# helpers

    def new_chat(self):
        return self.client.chats.create(
            model=self.MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=self.tools
            ),
        )

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name not in TOOL_FUNCTIONS:
            return json.dumps({"error": f"Unbekanntes Tool: {tool_name}"})
        try:
            return TOOL_FUNCTIONS[tool_name](**tool_input)
        except Exception as e:
            return json.dumps({"error": f"Tool-Fehler bei {tool_name}: {str(e)}"})
    
    @staticmethod
    def build_tools() -> list[types.Tool]:
        declarations = [
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parametersJsonSchema=t["input_schema"]
            )
            for t in ALL_TOOLS
        ]
        return [types.Tool(function_declarations=declarations)]

    @staticmethod
    def extract_text(response) -> str:
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return "Entschuldigung, ich konnte keine Antwort generieren."
        texts = [
            part.text
            for part in candidate.content.parts
            if part.text
        ]
        return "\n".join(texts) if texts else "Entschuldigung, ich konnte keine Antwort generieren."
