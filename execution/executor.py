from languages.python import PythonExecutor

class ExecutorFactory:

    # language can be added by adding language logic in /languages and adding entry in the _registry

    _registry = {
        "python": PythonExecutor,
    }

    @staticmethod
    def get_executor(language: str, source_code: str, function_name: str):
        executor_class = ExecutorFactory._registry.get(language)

        if not executor_class:
            raise ValueError("Unsupported language")

        return executor_class(source_code, function_name)
