from unrelevant.UnrelevantBase.Provider import BaseProvider
from unrelevant.exceptions.BaseExceptions import BaseError


class ConfigFileNotFoundError(BaseError):  # pragma: no cover
    """Exception raised for errors while accessing a non-existent config file.

    Attributes:
        config_file -- the name of the config file
    """

    def __init__(self):
        self.message = f"No config file found or could not be red."
        super().__init__(self.message)


class MissingParameterError(BaseError):  # pragma: no cover
    """Exception raised for config parameters not found.

    Attributes:
        parameter -- the name of the missing parameter
    """

    def __init__(self, parameter: str):
        self.message = f"Parameter not set correctly. Parameter: {parameter}"
        super().__init__(self.message)
