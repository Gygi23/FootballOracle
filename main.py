from agent.agent import FootballAIAgent
from agent.llm.gemini import GeminiLLM
# from agent.llm.anthropic import AnthropicLLM  ← eine Zeile tauschen

def main():
    print("╔══════════════════════════════════════════════╗")
    print("║     footballAI – WM 2026 Analyse Agent       ║")
    print("╚══════════════════════════════════════════════╝")
    print("Befehle: 'exit' zum Beenden, 'new' für neue Sitzung\n")

    agent = FootballAIAgent(llm=GeminiLLM())
    # agent = FootballAIAgent(llm=AnthropicLLM())  ← so wechselt man

    while True:
        try:
            user_input = input("Du: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAuf Wiedersehen!")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "new":
            agent.new_session()
            continue

        agent.chat(user_input)

if __name__ == "__main__":
    main()
