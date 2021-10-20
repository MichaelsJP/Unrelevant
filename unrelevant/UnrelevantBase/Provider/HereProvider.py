import logging

from geojson import FeatureCollection, Polygon, Feature
from routingpy import HereMaps

from unrelevant.UnrelevantBase.Provider.BaseProvider import BaseProvider
from unrelevant.exceptions.ProviderExceptions import ProfileNotImplementedError

logger = logging.getLogger(__name__)


class HereProvider(BaseProvider):
    def __init__(self, api_key: str, profile: str):
        super().__init__(name="here", api_key=api_key)
        self._api = HereMaps(api_key=self._api_key)
        self.profile = profile

    @BaseProvider.profile.setter
    def profile(self, profile):
        if "car" in profile:
            self._profile = "car"
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

    @staticmethod
    def _remap_linear_ring(linear_ring):
        split_linear_ring = []
        for coordinate in linear_ring:
            split = coordinate.split(",")
            split_linear_ring.append([float(split[1]), float(split[0])])
        return split_linear_ring

    def _component_to_multipolygon(self, components):
        allPolies = []
        for component in components:
            shell = self._remap_linear_ring(component['shape'])
            allPolies.append(Feature(geometry=Polygon([shell])))
        return allPolies

    def _response_to_geojson(self, response_data):
        polygons = list(
            map(lambda r: self._component_to_multipolygon(r['component']),
                response_data['response']['isoline']))
        if len(polygons) > 0:
            return FeatureCollection(polygons[0])
        else:
            return {}

    def isochrones(self, coordinates: [], iso_range, range_type: str):
        isochrones = self._api.isochrones(locations=coordinates,
                                          profile=self.profile,
                                          interval_type=range_type,
                                          intervals=iso_range).raw
        isochrones = self._response_to_geojson(isochrones)
        if isochrones.__contains__("features"):
            isochrones['features'] = [
                self._post_process_iso(isochrone)
                for isochrone in isochrones['features']
            ]
        return isochrones
