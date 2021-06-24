from yact.YactBase.Provider import BaseProvider
from yact.exceptions.BaseExceptions import BaseError


class IsochronesCalculationError(BaseError):  # pragma: no cover
    """Exception raised for errors while calculating isochrones.

    Attributes:
        dependency_name -- the name of the dependency
    """

    def __init__(self, coords: str, provider: BaseProvider):
        self.message = f"Error while generating Isochrones. Provider: {provider.provider_name}  | Coordinates: {coords}"
        super().__init__(self.message)
