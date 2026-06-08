from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def chat(self, user_message: str) -> str:
        pass

    @abstractmethod
    def new_session(self) -> None:
        pass