import datetime
import logging
import os

import contextily as ctx
import matplotlib
import matplotlib.pyplot as plt
from geopandas import GeoDataFrame
from ohsome import OhsomeClient
from openrouteservice.exceptions import ApiError
from routingpy.exceptions import RouterApiError

from yact.YactBase.Provider.BaseProvider import BaseProvider
from yact.exceptions.IsochronesExceptions import IsochronesCalculationError
from yact.exceptions.ProviderExceptions import WrongAPIKeyError

logger = logging.getLogger(__name__)


class BaseScenario(object):
    def __init__(self,
                 name: str,
                 filter_time: str,
                 filter_query: str,
                 provider: BaseProvider = None,
                 range_type: str = "time"):
        self._name = name
        self._provider = provider
        self._range_type = range_type
        self._filter_time = filter_time
        self._filter = filter_query
        self._ohsome_client = OhsomeClient(
            base_api_url="http://localhost:8080")
        self._geometry_results: {} = {}
        matplotlib.use("agg")
        logger.debug(
            "Base Scenario initialized with the following parameters:")
        logger.debug(f"Scenario name: {name}")
        logger.debug(f"Used filter time: {filter_time}")
        logger.debug(f"Used filter query: {filter_query}")
        logger.debug(f"Used provider: {provider.provider_name}")
        logger.debug(f"Used tange type: {range_type}")

    @property
    def scenario_name(self):
        return self._name

    def process(self, bbox):
        pass

    def _get_isochrones(self, features: [], ranges: []):
        isochrones: [] = []
        try:
            for feature in features['features']:
                coords = feature['geometry']['coordinates']
                isochrone = self._get_isochrone(coords=coords, ranges=ranges)
                isochrones.append(isochrone)
        except KeyError:
            logger.error(
                "Error reading the points geometry. The geometry seems broken."
            )
        except Exception as err:
            logger.error(err)
        return isochrones

    def _get_isochrone(self, coords: [], ranges: []) -> dict:
        try:
            return self._provider.isochrones(coords, ranges, self._range_type)
        except (RouterApiError, ApiError):
            raise WrongAPIKeyError(provider=self._provider)
        except Exception as err:
            raise IsochronesCalculationError(coords=coords,
                                             provider=self._provider)

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
            result.to_file(filename=file_path_geojson, driver='GeoJSON')
            result = result.to_crs(epsg=3857)
            ax = result.plot(figsize=(10, 10),
                             alpha=0.5,
                             edgecolor='r',
                             linewidth=3)
            ctx.add_basemap(ax)
            plt.title(
                f"Scenario: {self.scenario_name} | Provider: {self._provider.provider_name} | Range: {cleaned_name} seconds\n"
                + f"Profile: {self._provider.profile}")
            plt.savefig(file_path_png)
            plt.close()
            files.extend([file_path_geojson, file_path_png])
        return files

    def _get_points(self, bbox) -> dict:
        response = self._ohsome_client.elements.centroid.post(
            bboxes=bbox,
            time=self._filter_time,
            filter=self._filter,
            properties="tags")
        if 'features' not in response.data.keys():
            logger.warning("No results for the given coordinates.")
            return {}
        return response.data

    def __del__(self):
        del self._ohsome_client
