import datetime
import json
import geojson
import logging
import os

import contextily as ctx
import matplotlib
import matplotlib.pyplot as plt

from geopandas import GeoDataFrame
from ohsome import OhsomeClient
from openrouteservice.exceptions import ApiError
from routingpy.exceptions import RouterApiError

from unrelevant.UnrelevantBase.Provider.BaseProvider import BaseProvider
from unrelevant.exceptions.BaseExceptions import OhsomeExtentNotFoundError
from unrelevant.exceptions.IsochronesExceptions import IsochronesCalculationError
from unrelevant.exceptions.ProviderExceptions import WrongAPIKeyError

logger = logging.getLogger()


class BaseScenario(object):
    def __init__(self,
                 name: str,
                 filter_time: str,
                 filter_query: str,
                 provider: BaseProvider = None,
                 range_type: str = "time",
                 ohsome_api: str = "https://api.ohsome.org/v1"):
        self._name = name
        self._provider = provider
        self._range_type = range_type
        self._filter_time = filter_time
        self._filter = filter_query
        self._ohsome_client = OhsomeClient(base_api_url=ohsome_api)
        self._geometry_results: {} = {}
        self._ohsome_endpoint_spatial_extent = self._get_ohsome_spatial_extent(
        )
        self._ohsome_endpoint_temporal_extent = self._get_ohsome_temporal_extent(
        )
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

    def process(self):
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

    def _get_isochrone(self, coords: [], filter_query: str, ranges: [], _,
                       global_tqdm) -> dict:
        data = {}
        try:
            data = self._provider.isochrones(coords, ranges, self._range_type)
        except (RouterApiError) as err:
            logger.warning(
                f"API error calculating isochrone. Coords:{coords}, Ranges: {ranges}"
            )
            return {}
        except Exception as err:
            logger.warning(
                f"Unknown error calculating isochrone. Coords:{coords}, Ranges: {ranges}"
            )
            return {}
        global_tqdm.update()
        data['filterQuery'] = filter_query
        return data

    @staticmethod
    def write_scala_result(full_path_png, png_title, result: GeoDataFrame):
        """
        Write a single result with the given parameter as a geojson and png.
        Args:
            full_path_geojson: Fully qualified path to the geojson file.
            full_path_png: Fully qualified path to the png file.
            png_title: Title for the plot.
            result: Result object. Should be a GeodataFrame or Series.

        """
        if result.__class__ == GeoDataFrame:
            result = result.to_crs(epsg=3857)
            if result.columns.__contains__(
                    'city') and result.columns.__contains__('city'):
                result = result.sort_values('range', ascending=False)
                ax = result.plot(column="range",
                                 figsize=(10, 10),
                                 alpha=0.6,
                                 edgecolor='b',
                                 linewidth=0.7,
                                 legend=True,
                                 categorical=True,
                                 legend_kwds={'title': "Ranges(s)"})
            if result.columns.__contains__('range'):
                result = result.sort_values('range', ascending=False)
                ax = result.plot(column="range",
                                 figsize=(10, 10),
                                 alpha=0.6,
                                 edgecolor='b',
                                 linewidth=0.7,
                                 legend=True,
                                 categorical=True,
                                 legend_kwds={'title': "Ranges(s)"})
            else:
                ax = result.plot(figsize=(10, 10),
                                 alpha=0.6,
                                 edgecolor='b',
                                 linewidth=0.7)
            try:
                ctx.add_basemap(ax)
            except Exception as err:
                logger.warning(
                    f"Contextily had an error. This happens often as it's highly unstable. Error: {err}"
                )
            plt.title(png_title)
            plt.savefig(full_path_png)
            plt.close()

    @staticmethod
    def write_geo_result(full_path_geojson,
                         full_path_png,
                         png_title,
                         result: GeoDataFrame,
                         plot: bool = True):
        """
        Write a single result with the given parameter as a geojson and png.
        Args:
            full_path_geojson: Fully qualified path to the geojson file.
            full_path_png: Fully qualified path to the png file.
            png_title: Title for the plot.
            result: Result object. Should be a GeodataFrame or Series.

        """
        if result.__class__ == GeoDataFrame:
            with open(full_path_geojson, 'w') as f:
                json.dump(json.loads(result.to_json()), f)
            if plot:
                result = result.to_crs(epsg=3857)
                if result.columns.__contains__('range'):
                    result = result.sort_values('range', ascending=False)
                    ax = result.plot(column="range",
                                     figsize=(10, 10),
                                     alpha=0.6,
                                     edgecolor='b',
                                     linewidth=0.7,
                                     legend=True,
                                     categorical=True,
                                     legend_kwds={'title': "Ranges(s)"})
                else:
                    ax = result.plot(figsize=(10, 10),
                                     alpha=0.6,
                                     edgecolor='b',
                                     linewidth=0.7)
                try:
                    ctx.add_basemap(ax)
                except Exception as err:
                    logger.warning(
                        f"Contextily had an error. This happens often as it's highly unstable. Error: {err}"
                    )
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
        output_absolute_path = output_path + f"/{self.scenario_name}_{current_time}" + f"/{self._provider.provider_name}_" \
                                                                                       f"{self._provider.profile}"
        logger.info(f"Writing results to: {output_absolute_path}")

        # Make sure output folder exists
        if not os.path.exists(output_path +
                              f"/{self.scenario_name}_{current_time}"):
            os.makedirs(output_path + f"/{self.scenario_name}_{current_time}")

        result: GeoDataFrame
        files = []
        for name in self._geometry_results.keys():
            result = self._geometry_results.get(name)
            cleaned_name = str(name).strip('[').strip(']').replace(',', '_')
            file_path_geojson = output_absolute_path + f"_{cleaned_name}sec.geojson"
            file_path_png = output_absolute_path + f"_{cleaned_name}sec.png"
            png_title = f"Scenario: {self.scenario_name} | Provider: {self._provider.provider_name} | Range: {cleaned_name} seconds\nProfile: {self._provider.profile}"
            self.write_geo_result(file_path_geojson, file_path_png, png_title,
                                  result)
            files.extend([file_path_geojson, file_path_png])

            for i in result.index:
                file_path_png = output_absolute_path + f"_{cleaned_name}sec_{i}.png"
                file_path_geojson = output_absolute_path + f"_{cleaned_name}sec" + f"_{i}.geojson"
                png_title = f"Scenario: {self.scenario_name} | Provider: {self._provider.provider_name} | Range: {cleaned_name} seconds\nProfile: {self._provider.profile}\n{i}"
                row = result.loc[[i]]
                if 'Polygon' in row['geometry'].geom_type.values:
                    self.write_geo_result(file_path_geojson, file_path_png,
                                          png_title, row)

        return files

    def _get_points_by_bbox(self, bbox: str) -> dict:
        response = {}
        if bbox:
            response = self._ohsome_client.elements.centroid.post(
                bboxes=bbox,
                time=self._ohsome_endpoint_temporal_extent,
                filter=self._filter,
                properties="tags")
        if 'features' in response.data.keys():
            return response.data
        logger.warning("No results for the given coordinates.")
        return {}

    def __del__(self):
        del self._ohsome_client

    def _get_ohsome_spatial_extent(self):
        ohsome_metadata = self._ohsome_client.metadata
        ohsome_extent = None
        if 'extractRegion' in ohsome_metadata and 'spatialExtent' in ohsome_metadata[
                'extractRegion']:
            feature = {
                "type": "Feature",
                "geometry": ohsome_metadata['extractRegion']['spatialExtent']
            }
            return geojson.FeatureCollection([feature])
        raise OhsomeExtentNotFoundError(self._ohsome_client.base_api_url)

    def _get_ohsome_temporal_extent(self):
        ohsome_metadata = self._ohsome_client.metadata
        ohsome_extent = None
        if 'extractRegion' in ohsome_metadata and 'temporalExtent' in ohsome_metadata[
                'extractRegion']:
            return ohsome_metadata['extractRegion']['temporalExtent'][
                'toTimestamp']
        raise OhsomeExtentNotFoundError(self._ohsome_client.base_api_url)
