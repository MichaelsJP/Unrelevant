import datetime
import json

import logging
import os

import contextily as ctx

from geopandas import GeoDataFrame
import geopandas as gp
from yact.YactBase.Provider.BaseProvider import BaseProvider
from yact.YactBase.scenarios.BaseScenario import BaseScenario
from yact.exceptions.BaseExceptions import OhsomeQueryError
import tqdm
from tqdm_multiprocess import TqdmMultiProcessPool
from sqlalchemy import create_engine
from geojson.geometry import MultiPolygon
from geoalchemy2 import Raster, Geometry
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer

logger = logging.getLogger()

Base = declarative_base()


class PopulationFetcher(Base):
    id = Column(Integer, primary_key=True)
    rast = Column(Raster)
    __tablename__ = 'population'

    def __init__(self, url, port, db, user, password):
        self._url = url
        self._port = int(port)
        self._db = db
        self._user = user
        self._password = password
        self._connection = None

    def _connect_to_db(self):
        engine = create_engine(
            f'postgresql://{self._user}:{self._password}@{self._url}:{self._port}/{self._db}'
        )
        self._connection = engine.connect()

    def _execute_query(self, query):
        result = None
        if not self._connection:
            self._connect_to_db()
        try:
            result = self._connection.execute(query).fetchall()
        except Exception as err:
            raise err
        finally:
            self._connection.close()
            self._connection = None
            return result[0][0] if result else 0

    def get_population_data(self, wkt_geom: str):
        query = f"""
    SELECT(
        St_SummaryStats(
            ST_Clip(
                rast,1,st_geomfromtext('{wkt_geom}', 4326), true)
            )
        ).sum
    FROM
        wpop
    WHERE
        st_intersects(
                rast,
                st_geomfromtext('{wkt_geom}', 4326)
        );
        """
        return self._execute_query(query)


class RecreationScenario(BaseScenario):
    def __init__(self,
                 provider: BaseProvider,
                 cities: [],
                 ranges: [],
                 range_type: str = "time",
                 ohsome_api: str = "https://api.ohsome.org/v1",
                 tags: {} = None,
                 threads: int = 1,
                 population_fetcher: PopulationFetcher = None):
        self._ranges: [] = ranges
        self._cities: [] = cities
        self._tags: dict = tags
        self._threads: int = threads
        self._population_fetcher = population_fetcher
        super().__init__(name="recreation",
                         filter_time="2018-08-12",
                         filter_query="",
                         provider=provider,
                         range_type=range_type,
                         ohsome_api=ohsome_api)
        logger.debug(
            "Recreation Scenario initialized with the following parameters:")
        logger.debug(f"Used ranges: {self._ranges}")
        logger.debug(f"Used profile: {self._provider.profile}")

    def _get_city_bounds(self, bbox) -> dict:
        city_data = {}
        logger.info("Getting city boundaries")
        for city_name in self._cities:
            logger.info(f"Getting city boundary for: {city_name}")
            try:
                response = self._ohsome_client.elements.geometry.post(
                    bboxes=bbox,
                    time=self._ohsome_endpoint_temporal_extent,
                    filter=f"boundary=administrative and name={city_name}",
                    # filter=f"type:relation and boundary=administrative and name=heidelberg",
                    properties="tags")
            except Exception as err:
                raise OhsomeQueryError(err.__str__())
            if response.data and len(response.data['features']):
                city_data[city_name] = {}
                city_data[city_name]['boundary'] = response.data
            else:
                logger.info(f"Couldn't find city data for: {city_name}")
        return city_data

    def _get_city_pois_by_bpolys(self, bpolys: str) -> dict:
        data = {}
        for category in self._tags.keys():
            filter_query = ""
            for key, value in self._tags.get(category).items():
                if len(filter_query) > 0:
                    filter_query = f"{filter_query} or {key}={value}"
                else:
                    filter_query = f"{key}={value}"
            if len(filter_query):
                response = self._ohsome_client.elements.centroid.post(
                    bpolys=bpolys,
                    time=self._ohsome_endpoint_temporal_extent,
                    filter=filter_query,
                    properties="tags")
                if 'features' in response.data.keys():
                    data[category] = response.data
                    data[category]['filterQuery'] = filter_query
                    logger.info(
                        f"{len(data[category]['features'])} POIs found for category {category}"
                    )
                else:
                    logger.debug(f"No POIs with category {category} found.")
            else:
                logger.debug(
                    f"No Filter Query constructed for category {category}.")
        return data

    @staticmethod
    def _done_callback(result):  # pragma: no cover
        """
        Success catch function for completed threads. No deep usage.
        """
        pass

    @staticmethod
    def _on_error(result):  # pragma: no cover
        """
        Error catch function for aborted or failed threads. No deep usage besides printing an error.
        @param result:
        """
        logger.error(f"Error calculating result for: {result}")

    def _get_isochrones(
            self,
            features: [],
            ranges: [],
            threading_description: str = "Calculating Isochrones Multithreaded"
    ):
        isochrones: {} = {}
        try:
            filter_query = features['filterQuery']
            task = [[
                feature['geometry']['coordinates'], feature['properties']
            ] for feature in features['features']]
            initial_tasks = [(self._get_isochrone, (
                task[i][0],
                task[i][1],
                ranges,
            )) for i in range(len(task))]
            pool = TqdmMultiProcessPool(self._threads)
            with tqdm.tqdm(total=len(initial_tasks),
                           dynamic_ncols=True,
                           unit="Isochrones") as global_progress:
                global_progress.set_description(threading_description)
                processed_isochrones = pool.map(global_progress, initial_tasks,
                                                self._on_error,
                                                self._done_callback)

            for processed_isochrone in processed_isochrones:
                for key, value in processed_isochrone['filterQuery'].items():
                    if f"{key}={value}" in filter_query and f"{key}={value}" not in isochrones:
                        isochrones[f"{key}={value}"] = [processed_isochrone]
                        continue
                    elif f"{key}={value}" in filter_query:
                        isochrones[f"{key}={value}"].append(
                            processed_isochrone)
                        continue
        except KeyError:
            logger.error(
                "Error reading the points geometry. The geometry seems broken."
            )
        except Exception as err:
            logger.error(err)
        return isochrones

    def _postprocess_city_data(self, isochrones: [], points: [], ranges,
                               clip_region):
        gdf_category = GeoDataFrame()
        gdf_tags = GeoDataFrame()
        gdf_tags_dissolved = GeoDataFrame()
        gdf_points = GeoDataFrame()
        boundary = GeoDataFrame.from_features(clip_region, crs="EPSG:4326")
        total_population = self._population_fetcher.get_population_data(
            boundary.geometry.get(0).to_wkt())
        for tag in isochrones:
            if not isinstance(isochrones[tag], list):
                continue
            for feature in isochrones[tag]:
                if len(feature.values()) <= 0:
                    continue
                if gdf_tags.empty:
                    gdf_tags = GeoDataFrame.from_features(feature)
                    gdf_tags['tag1'] = tag

                else:
                    gdf_tags = gdf_tags.append(
                        GeoDataFrame.from_features(feature))
                    gdf_tags['tag1'] = gdf_tags['tag1'].fillna(tag)
        if not gdf_tags.empty:
            gdf_tags['range'] = gdf_tags['value']
            gdf_tags['tag'] = gdf_tags['tag1']
            gdf_tags.range = gdf_tags.range.astype(int)
            gdf_tags = gdf_tags.set_crs(epsg=4326)
            gdf_category = gdf_tags.dissolve(by=['value'])
            gdf_tags_dissolved = gdf_tags.dissolve(by=['value', 'tag1'])

            # Generate the dissolved tags and generate the POI count
            groups = gdf_tags.groupby(['range', 'tag'])
            gdf_tags_dissolved['count_pois'] = 0
            for group in groups:
                iso_range = group[0][0]
                iso_tag = group[0][1]
                count = len(group[1])
                filter_query = (gdf_tags_dissolved.range == iso_range) & (
                    gdf_tags_dissolved.tag == iso_tag)
                gdf_tags_dissolved.loc[filter_query, 'count_pois'] = count

            # Generate the dissolved categories and generate the POI count
            groups = gdf_tags.groupby(['range'])
            gdf_category['count_pois'] = 0
            for group in groups:
                iso_range = group[0]
                count = len(group[1])
                filter_query = (gdf_category.range == iso_range)
                gdf_category.loc[filter_query, 'count_pois'] = count

            gdf_category = gp.clip(gdf_category, boundary)
            gdf_tags_dissolved = gp.clip(gdf_tags_dissolved, boundary)
            gdf_category['population'] = 0.0
            gdf_tags_dissolved['population'] = 0.0
            gdf_category['total_population_percentage'] = 0.0
            gdf_tags_dissolved['total_population_percentage'] = 0.0
            gdf_category['total_population'] = total_population
            gdf_tags_dissolved['total_population'] = total_population

            for geometry_key in gdf_tags_dissolved.geometry.keys():
                geometry: MultiPolygon = gdf_tags_dissolved.geometry.get(
                    geometry_key)
                population = self._population_fetcher.get_population_data(
                    geometry.to_wkt())
                if population is not None:
                    gdf_tags_dissolved.at[geometry_key,
                                          'population'] = population
                    gdf_tags_dissolved.at[
                        geometry_key, 'total_population_percentage'] = (
                            population / total_population) * 100
            for geometry_key in gdf_category.geometry.keys():
                geometry: MultiPolygon = gdf_category.geometry.get(
                    geometry_key)
                population = self._population_fetcher.get_population_data(
                    geometry.to_wkt())
                if population is not None:
                    gdf_category.at[geometry_key, 'population'] = population
                    gdf_category.at[geometry_key,
                                    'total_population_percentage'] = (
                                        population / total_population) * 100

            gdf_category['population_poi_ratio'] = gdf_category[
                'population'] / gdf_category['count_pois']
            gdf_tags_dissolved['population_poi_ratio'] = gdf_tags_dissolved[
                'population'] / gdf_tags_dissolved['count_pois']

            gdf_category = gdf_category.drop(
                columns=["tag", "tag1", "group_index"])
            gdf_tags_dissolved = gdf_tags_dissolved.drop(
                columns=["group_index"])

            # Prepare for export
            gdf_points: GeoDataFrame = GeoDataFrame.from_features(points)
            gdf_tags_dissolved = gdf_tags_dissolved.set_crs(epsg=4326)
            gdf_category = gdf_category.set_crs(epsg=4326)
        return gdf_category, gdf_tags_dissolved, gdf_points

    def _get_cities_data(self, bbox):
        # TODO redo after development
        cities_data = self._get_city_bounds(bbox)
        # with open(
        #         "/home/jules/workspace/University/Unrelevant/data/test_city_data_heidelberg_karlsruhe.json",
        #         "r") as f:
        #     cities_data = json.load(f)
        # TODO redo after development

        for city in cities_data:
            logger.info(f"Getting POIs for {city}")

            # TODO redo after development
            pois = self._get_city_pois_by_bpolys(
                bpolys=json.dumps(cities_data[city]['boundary']))
            if not len(pois):
                logger.info(
                    f"No POIs found for city: {city}. Excluding it from the results."
                )
                cities_data.pop(city)
                continue
            cities_data[city]['pois'] = pois
            del pois
            # TODO redo after development
            if not "isochrones" in cities_data[city]:
                cities_data[city]['isochrones'] = {}
            city_boundary = cities_data[city]['boundary']
            gdf_city = GeoDataFrame()
            gdf_city['count_pois'] = 0

            boundary = GeoDataFrame.from_features(city_boundary,
                                                  crs="EPSG:4326")
            total_population = self._population_fetcher.get_population_data(
                boundary.geometry.get(0).to_wkt())

            for category in cities_data[city]['pois']:
                logger.info(
                    f"Getting and processing Isochrones for {city} and category {category}"
                )
                # TODO redo after development
                isochrones = self._process_isochrones(
                    cities_data[city]['pois'][category],
                    threading_description=f"Calculating Isochrones for {city}")
                # isochrones = cities_data[city]['isochrones'][category]
                # TODO redo after development

                gdf_category, gdf_tags, gdf_points = self._postprocess_city_data(
                    isochrones,
                    cities_data[city]['pois'][category],
                    self._ranges,
                    clip_region=city_boundary)
                gdf_category['city'] = city
                gdf_category['category'] = category
                gdf_tags['city'] = city
                gdf_tags['category'] = category
                gdf_points['city'] = city

                gdf_city['count_pois'] += len(gdf_points)
                gdf_city = gdf_city.append(gdf_category)

                if category not in cities_data[city]['isochrones']:
                    cities_data[city]['isochrones'][category] = {}
                if "results_category" not in cities_data[city]['isochrones'][
                        category]:
                    cities_data[city]['isochrones'][category][
                        'results_category'] = {}
                if "results_tags" not in cities_data[city]['isochrones'][
                        category]:
                    cities_data[city]['isochrones'][category][
                        'results_tags'] = {}
                if "results_points" not in cities_data[city]['isochrones'][
                        category]:
                    cities_data[city]['isochrones'][category][
                        'results_points'] = {}
                cities_data[city]['isochrones'][category][
                    'results_category'] = json.loads(gdf_category.to_json())
                cities_data[city]['isochrones'][category][
                    'results_tags'] = json.loads(gdf_tags.to_json())
                cities_data[city]['isochrones'][category][
                    'results_points'] = json.loads(gdf_points.to_json())

            # Total statistics
            gdf_city = gdf_city.dissolve()
            gdf_city['population'] = 0.0
            gdf_city['total_population_percentage'] = 0.0
            gdf_city['total_population'] = total_population
            for geometry_key in gdf_city.geometry.keys():
                geometry: MultiPolygon = gdf_city.geometry.get(geometry_key)
                population = self._population_fetcher.get_population_data(
                    geometry.to_wkt())
                if population is not None:
                    gdf_city.at[geometry_key, 'population'] = population
                    gdf_city.at[geometry_key,
                                'total_population_percentage'] = (
                                    population / total_population) * 100

            gdf_city['population_poi_ratio'] = gdf_city[
                'population'] / gdf_city['count_pois']

            #  Drop unneeded columns
            gdf_city = gdf_city.drop(columns=["range", "category"])

            if "results_total" not in cities_data[city]['isochrones']:
                cities_data[city]['isochrones']['results_total'] = {}
            cities_data[city]['isochrones']['results_total'] = json.loads(
                gdf_city.to_json())
        return cities_data

    def _process_isochrones(
            self,
            point_features,
            threading_description: str = "Calculating Isochrones Multithreaded"
    ):
        isochrones = self._get_isochrones(
            features=point_features,
            ranges=self._ranges,
            threading_description=threading_description)
        return isochrones

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

        # Make sure output folder exists
        if not os.path.exists(output_path +
                              f"/{self.scenario_name}_{current_time}"):
            os.makedirs(output_path + f"/{self.scenario_name}_{current_time}")

        files = []
        comparison_total = gp.GeoDataFrame()
        comparison_categories = gp.GeoDataFrame()
        comparison_tags = gp.GeoDataFrame()
        comparison_points = gp.GeoDataFrame()
        for city in self._geometry_results.keys():
            city_data = self._geometry_results.get(city)['isochrones']
            comparison_total = comparison_total.append(
                gp.GeoDataFrame.from_features(city_data['results_total']))
            for category in city_data.keys():
                # Generate city details
                if category == 'results_total':
                    continue
                comparison_categories = comparison_categories.append(
                    gp.GeoDataFrame.from_features(
                        city_data[category]['results_category']))
                comparison_tags = comparison_tags.append(
                    gp.GeoDataFrame.from_features(
                        city_data[category]['results_tags']))
                comparison_points = comparison_points.append(
                    gp.GeoDataFrame.from_features(
                        city_data[category]['results_points']))

        comparison_total = comparison_total.set_crs(crs=4326)
        comparison_categories = comparison_categories.set_crs(crs=4326)
        comparison_tags = comparison_tags.set_crs(crs=4326)
        comparison_points = comparison_points.set_crs(crs=4326)

        cleaned_range = str(self._ranges).strip('[').strip(']')

        comparison_total_file_path_geojson = output_absolute_path + f"_comparison_total.geojson"
        comparison_categories_file_path_geojson = output_absolute_path + f"_comparison_categories.geojson"
        comparison_tags_file_path_geojson = output_absolute_path + f"_comparison_tags.geojson"
        comparison_points_file_path_geojson = output_absolute_path + f"_comparison_points.geojson"

        comparison_total_file_path_png = output_absolute_path + f"_comparison_total.png"
        comparison_categories_file_path_png = output_absolute_path + f"_comparison_categories.png"
        comparison_tags_file_path_png = output_absolute_path + f"_comparison_tags.png"
        comparison_points_file_path_png = output_absolute_path + f"_comparison_points.png"

        comparison_total_png_title = f"Scenario: {self.scenario_name} - Comparison Total | Provider: {self._provider.provider_name} | Range: {cleaned_range} seconds\nProfile: {self._provider.profile}"
        comparison_categories_png_title = f"Scenario: {self.scenario_name} - Comparison Categories | Provider: {self._provider.provider_name} | Range: {cleaned_range} seconds\nProfile: {self._provider.profile}"
        comparison_tags_png_title = f"Scenario: {self.scenario_name} - Comparison Tags | Provider: {self._provider.provider_name} | Range: {cleaned_range} seconds\nProfile: {self._provider.profile}"
        comparison_points_png_title = f"Scenario: {self.scenario_name} - Comparison Points | Provider: {self._provider.provider_name} | Range: {cleaned_range} seconds\nProfile: {self._provider.profile}"

        self.write_result(comparison_total_file_path_geojson,
                          comparison_total_file_path_png,
                          comparison_total_png_title, comparison_total)
        self.write_result(comparison_categories_file_path_geojson,
                          comparison_categories_file_path_png,
                          comparison_categories_png_title,
                          comparison_categories)
        self.write_result(comparison_tags_file_path_geojson,
                          comparison_tags_file_path_png,
                          comparison_tags_png_title, comparison_tags)
        self.write_result(comparison_points_file_path_geojson,
                          comparison_points_file_path_png,
                          comparison_points_png_title, comparison_points)
        files.extend([
            [
                comparison_total_file_path_geojson,
                comparison_total_file_path_png
            ],
            [
                comparison_categories_file_path_geojson,
                comparison_categories_file_path_png
            ],
            [comparison_tags_file_path_geojson, comparison_tags_file_path_png],
            [
                comparison_points_file_path_geojson,
                comparison_points_file_path_png
            ],
        ])
        return files

    def process(self, bbox):
        cities_data = self._get_cities_data(bbox)
        logger.debug("Writing cities data to temporary file.")
        with open(
                "/home/jules/workspace/University/Unrelevant/data/test_city_data_heidelberg_karlsruhe.json",
                "w") as f:
            json.dump(cities_data, f)
        # TODO remove after development
        with open(
                "/home/jules/workspace/University/Unrelevant/data/test_city_data_heidelberg_karlsruhe.json",
                "r") as f:
            cities_data = json.load(f)
        self._geometry_results = cities_data
