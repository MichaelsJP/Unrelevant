import logging

from routingpy import MapboxValhalla, Valhalla

from unrelevant.UnrelevantBase.Provider.BaseProvider import BaseProvider
from unrelevant.exceptions.ProviderExceptions import ProfileNotImplementedError

logger = logging.getLogger()


class ValhallaProvider(BaseProvider):
    def __init__(self, api_key: str, profile: str, base_url: str = None):
        super().__init__(name="valhalla", api_key=api_key)
        if base_url:
            self._api = Valhalla(base_url=base_url, api_key=self._api_key)
        else:
            self._api = MapboxValhalla(api_key=self._api_key)
        self.profile = profile

    @BaseProvider.profile.setter
    def profile(self, profile):
        if "car" in profile:
            self._profile = "auto"
        elif "pedestrian" in profile:
            self._profile = "pedestrian"
        else:
            raise ProfileNotImplementedError(profile, self._name)

    def _post_process_iso(self, isochrone: dict):
        if isochrone.keys().__contains__("properties"):
            if not isochrone['properties'].__contains__("group_index"):
                isochrone['properties']['group_index'] = 0
        else:
            isochrone['properties'] = {}
            isochrone['properties']['group_index'] = 0
        return isochrone

    def isochrones(self, coordinates: [], iso_range, range_type: str):
        isochrones = self._api.isochrones(locations=coordinates,
                                          profile=self.profile,
                                          polygons=True,
                                          denoise=1,
                                          intervals=iso_range).raw
        if isochrones.__contains__("features"):
            isochrones['features'] = [
                self._post_process_iso(isochrone)
                for isochrone in isochrones['features']
            ]
        return isochrones
