import json
import logging
from geopandas import GeoDataFrame

from unrelevant.UnrelevantBase.Provider.BaseProvider import BaseProvider
from unrelevant.UnrelevantBase.scenarios.BaseScenario import BaseScenario

logger = logging.getLogger()


class VaccinationScenario(BaseScenario):
    def __init__(self,
                 provider: BaseProvider,
                 ranges: [],
                 range_type: str = "time",
                 ohsome_api: str = "https://api.ohsome.org/v1"):
        self._ranges: [] = ranges
        super().__init__(
            name="vaccination",
            filter_time="2020-01-01",
            filter_query=
            "healthcare:speciality=vaccination or vaccination=covid19 or "
            "healthcare=vaccination_centre",
            provider=provider,
            range_type=range_type,
            ohsome_api=ohsome_api)
        logger.debug(
            "Vaccination Scenario initialized with the following parameters:")
        logger.debug(f"Used ranges: {ranges}")

    def _postprocess(self, isochrones: [], points: []):
        gdf = GeoDataFrame()
        for collection in isochrones:
            if len(collection.values()) <= 0:
                continue
            if gdf.empty:
                gdf = GeoDataFrame.from_features(collection).dissolve(
                    by="group_index", aggfunc='sum')
            else:
                gdf = gdf.append(
                    GeoDataFrame.from_features(collection).dissolve(
                        by="group_index", aggfunc='sum'))
        if not gdf.empty:
            gdf = gdf.dissolve(by="group_index", aggfunc='sum')
            gdf = gdf.append(GeoDataFrame.from_features(points))
            gdf = gdf.set_crs(epsg=4326)
            self._geometry_results[str(self._ranges)] = gdf
        else:
            logger.warning(
                "Results were empty. Check the error logs or try another bounding box."
            )

    def process(self, bbox):
        point_features = self._get_points_by_bbox(bbox)
        isochrone_features = self._get_isochrones(features=point_features,
                                                  ranges=self._ranges)
        self._postprocess(isochrone_features, point_features)
