import logging
from abc import ABCMeta

from unrelevant.exceptions.ProviderExceptions import MissingAPIKeyError

logger = logging.getLogger()


class BaseProvider(metaclass=ABCMeta):
    def __init__(self, name: str, api_key: str):
        self._name = name
        if not api_key or len(api_key) <= 0:
            raise MissingAPIKeyError(self)
        self._api_key = api_key
        logger.debug(
            "Base Provider initialized with the following arguments: ")
        logger.debug(f"Provider name: {name}")
        logger.debug(f"Provider name: {api_key}")
        self._profile = None

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        self._profile = profile

    @property
    def provider_name(self):
        return self._name

    def isochrones(self, coordinates: [], iso_range, range_type: str):
        pass
