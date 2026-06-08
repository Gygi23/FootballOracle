from agent.llm.base import BaseLLM

class FootballAIAgent:
    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def chat(self, user_message: str) -> str:
        print(f"\n{'='*60}")
        print(f"USER: {user_message}")
        print(f"{'='*60}")
        response = self.llm.chat(user_message)
        print(f"\nASSISTANT: {response}")
        return response
 
    def new_session(self) -> None:
        self.llm.new_session()
