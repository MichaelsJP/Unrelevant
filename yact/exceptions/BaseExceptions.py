class BaseError(Exception):
    """Base class for exceptions in this module."""
    pass


class ProviderNotImplementedError(BaseError):
    """Exception raised for errors while accessing provider currently not implemented.

    Attributes:
        expression -- wrong algorithm
    """

    def __init__(self, expression: str):  # pragma: no cover
        self.expression = expression
        self.message = f"Chosen provider not found or not implemented {expression}"
        super().__init__(self.message)


class ScenarioNotImplementedError(BaseError):
    """Exception raised for errors while accessing a scenario currently not implemented.

    Attributes:
        expression -- wrong algorithm
    """

    def __init__(self, expression: str):  # pragma: no cover
        self.expression = expression
        self.message = f"Chosen scenario not found or not implemented {expression}"
        super().__init__(self.message)


class IndexAccessError(BaseError):  # pragma: no cover
    """Exception raised for errors while accessing an indexed based structure.

        Attributes:
            expression -- index
        """

    def __init__(self, row: int, column: int, message: str = None):
        self.expression = f"row: {row}, column: {column}"
        if not message:
            self.message = f"Out of bounds error for index row: {row}, column: {column}"
        else:
            self.message = message
        super().__init__(self.message)
