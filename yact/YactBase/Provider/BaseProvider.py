import logging
from abc import ABCMeta

from yact.exceptions.ProviderExceptions import MissingAPIKeyError

logger = logging.getLogger(__name__)


class BaseProvider(metaclass=ABCMeta):
    def __init__(self, name: str, api_key: str):
        if len(api_key) <= 0:
            raise MissingAPIKeyError(self.provider_name)
        self._api_key = api_key
        self._name = name
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
