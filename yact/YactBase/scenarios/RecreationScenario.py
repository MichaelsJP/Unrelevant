import json
import logging
import datetime
import os
import contextily as ctx

from geopandas import GeoDataFrame
import matplotlib.pyplot as plt

from yact.YactBase.Provider.BaseProvider import BaseProvider
from yact.YactBase.scenarios.BaseScenario import BaseScenario

logger = logging.getLogger(__name__)


class RecreationScenario(BaseScenario):
    def __init__(self, provider: BaseProvider, range_type: str = "time"):
        self._ranges_pedestrian: [] = [600, 1200, 1800, 3600]
        self._ranges_bicycle: [] = [600, 1200, 1800, 3600]
        self._ranges_car: [] = [600, 1200, 1800, 3600]
        super().__init__(
            name="recreation",
            filter_time="2020-01-01",
            filter_query=
            "leisure=nature_reserve or leisure=swimming_area or water=lake or historic=castle",
            provider=provider,
            range_type=range_type)
        logger.debug(
            "Recreation Scenario initialized with the following parameters:")
        logger.debug(f"Used pedestrian ranges: {self._ranges_pedestrian}")
        logger.debug(f"Used bicycle ranges: {self._ranges_bicycle}")
        logger.debug(f"Used car ranges: {self._ranges_car}")
        logger.debug(f"Used profiles: pedestrian, bicycle, car")

    def _get_isochrones(self, features: [], ranges: []):
        isochrones: {} = {}
        try:
            for feature in features['features']:
                coords = feature['geometry']['coordinates']
                isochrone = self._get_isochrone(coords=coords, ranges=ranges)
                for key, value in feature['properties'].items():
                    if f"{key}={value}" in self._filter and f"{key}={value}" not in isochrones:
                        isochrones[f"{key}={value}"] = [isochrone]
                        break
                    elif f"{key}={value}" in self._filter:
                        isochrones[f"{key}={value}"].append(isochrone)
                        break
        except KeyError:
            logger.error(
                "Error reading the points geometry. The geometry seems broken."
            )
        except Exception as err:
            logger.error(err)
        return isochrones

    @staticmethod
    def write_result(full_path_geojson, full_path_png, png_title, result):
        with open(full_path_geojson, 'w') as f:
            json.dump(json.loads(result.to_json()), f)
        result = result.to_crs(epsg=3857)
        ax = result.plot(figsize=(10, 10),
                         alpha=0.5,
                         edgecolor='r',
                         linewidth=3)
        ctx.add_basemap(ax)
        plt.title(png_title)
        plt.savefig(full_path_png)
        plt.close()

    def write_results(self, output_path: str) -> []:
        """
        Write the results to file. If no results are present, nothing will be written.
        The files are written with the file name and file extension from the input file with some algorithm related additions.
        @param output_path: Output path where the results should be stored.

        @return: Returns the paths from the written data.

        """
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_absolute_path = output_path + f"/{self.scenario_name}_" \
                                             f"{self._provider.provider_name}_" \
                                             f"{self._provider.profile}"

        # Make sure output folder exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        result: GeoDataFrame
        files = []
        for name in self._geometry_results.keys():
            result = self._geometry_results.get(name)
            cleaned_name = str(name).strip('[').strip(']').replace(',', '_')
            file_path_geojson = output_absolute_path + f"_{cleaned_name}sec" + f"_{current_time}.geojson"
            file_path_png = output_absolute_path + f"_{cleaned_name}sec" + f"_{current_time}.png"
            png_title = f"Scenario: {self.scenario_name} | Provider: {self._provider.provider_name} | Range: {cleaned_name} seconds\nProfile: {self._provider.profile}"
            self.write_result(file_path_geojson, file_path_png, png_title,
                              result)
            files.extend([file_path_geojson, file_path_png])
        return files

    def _postprocess_isochrones(self, isochrones: [], points: [], ranges):
        gdf = GeoDataFrame()
        for category in isochrones:
            for feature in isochrones[category]:
                if len(feature.values()) <= 0:
                    continue
                if gdf.empty:
                    gdf = GeoDataFrame.from_features(feature)
                    gdf['category1'] = category

                else:
                    gdf = gdf.append(GeoDataFrame.from_features(feature))
                    gdf['category1'] = gdf['category1'].fillna(category)
        if not gdf.empty:
            gdf['range'] = gdf['value']
            gdf['category'] = gdf['category1']
            gdf.range = gdf.range.astype(int)
            gdf = gdf.set_crs(epsg=4326)
            gdf.range = gdf.range.fillna(0)
            gdf = gdf.dissolve(by=['value', 'category1'])
            gdf: GeoDataFrame = gdf.append(GeoDataFrame.from_features(points))
            self._geometry_results[str(ranges)] = gdf
            return gdf

        # TODO: The category column now represents the correct geometry. Find a way to remain the category
        # Maybe split them into groups by category and then merge them in the groups
        else:
            logger.warning(
                "Results were empty. Check the error logs or try another bounding box."
            )

    def _process_pedestrian(self, point_features):
        self._provider.profile = 'pedestrian'
        isochrones_pedestrian = self._get_isochrones(
            features=point_features, ranges=self._ranges_pedestrian)
        postprocessed_isochrones = self._postprocess_isochrones(
            isochrones_pedestrian, point_features, self._ranges_pedestrian)
        return postprocessed_isochrones

    def process(self, bbox):
        point_features = self._get_points(bbox)
        data_pedestrian = self._process_pedestrian(point_features)
        print("")
