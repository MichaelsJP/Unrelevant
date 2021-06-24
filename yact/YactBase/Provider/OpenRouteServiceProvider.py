import logging

from openrouteservice import Client

from yact.YactBase.Provider.BaseProvider import BaseProvider
from yact.exceptions.ProviderExceptions import ProfileNotImplementedError

logger = logging.getLogger(__name__)


class OpenRouteServiceProvider(BaseProvider):
    def __init__(self, api_key: str, profile: str):
        super().__init__(name="ors", api_key=api_key)
        self._api = Client(key=self._api_key)
        self.profile = profile

    @BaseProvider.profile.setter
    def profile(self, profile):
        if profile is None:
            self._profile = ""
        if "car" in profile:
            self._profile = "driving-car"
        elif "pedestrian" in profile:
            self._profile = "foot-walking"
        else:
            raise ProfileNotImplementedError(profile, self._name)

    def isochrones(self, coordinates: [], iso_range, range_type):
        return self._api.isochrones(locations=[coordinates],
                                    profile=self.profile,
                                    range=iso_range,
                                    smoothing=0,
                                    range_type=range_type,
                                    validate=False,
                                    attributes=['total_pop'])
