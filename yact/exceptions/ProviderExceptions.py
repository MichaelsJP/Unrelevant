from yact.YactBase.Provider import BaseProvider
from yact.exceptions.BaseExceptions import BaseError


class ProfileNotImplementedError(BaseError):  # pragma: no cover
    """Exception raised for errors while accessing a non-existent profile.

    Attributes:
        profile -- the name of the profile
        provider -- the name of the provider
    """

    def __init__(self, profile: str, provider: BaseProvider):
        self.message = f"Profile not implemented. Provider: {provider.provider_name}  | Profile: {profile}"
        super().__init__(self.message)


class MissingAPIKeyError(BaseError):  # pragma: no cover
    """Exception raised for errors when no api key is set.

    Attributes:
        provider -- the name of the provider
    """

    def __init__(self, provider: BaseProvider):
        self.message = f"API Key not set correctly. Provider: {provider.provider_name}"
        super().__init__(self.message)


class WrongAPIKeyError(BaseError):  # pragma: no cover
    """Exception raised for errors when the api key is set but rejected.

    Attributes:
        provider -- the name of the provider
    """

    def __init__(self, provider: BaseProvider):
        self.message = f"API Key set but wrong/rejected. Provider: {provider.provider_name}"
        super().__init__(self.message)
