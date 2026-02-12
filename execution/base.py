# These are the functions which needs to be implemented by all of the executors of the languages.

from abc import ABC, abstractmethod
from typing import Dict,Any

class BaseExecutor(ABC):

    def __init__(self, code: str, function_name: str):
        self.code = code
        self.function_name = function_name
    
    @abstractmethod
    def compile(self) -> None:
        pass

    @abstractmethod
    def run(self, test_input: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass
