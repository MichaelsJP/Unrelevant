from unrelevant.exceptions.BaseExceptions import BaseError


class DependencyNotFoundError(BaseError):  # pragma: no cover
    """Exception raised for errors while checking for needed dependencies.

    Attributes:
        dependency_name -- the name of the dependency
    """

    def __init__(self, dependency_name: str):
        self.expression = str(dependency_name)
        self.message = f"Dependency not installed: {dependency_name}"
        super().__init__(self.message)
