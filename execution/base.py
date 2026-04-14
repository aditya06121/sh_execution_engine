from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseExecutor(ABC):

    def __init__(self, code: str, function_name: str):
        self.code = code
        self.function_name = function_name

    @abstractmethod
    async def compile(self) -> None:
        pass

    @abstractmethod
    async def run(self, test_input: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        pass
