import json
import logging

from geopandas import GeoDataFrame
import geopandas as gp
from yact.YactBase.Provider.BaseProvider import BaseProvider
from yact.YactBase.scenarios.BaseScenario import BaseScenario
from yact.exceptions.BaseExceptions import OhsomeQueryError
import tqdm
from tqdm_multiprocess import TqdmMultiProcessPool
from sqlalchemy import create_engine

logger = logging.getLogger()


class PopulationFetcher:
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
            return result[0][0] if result else None

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
                 range_type: str = "time",
                 ohsome_api: str = "https://api.ohsome.org/v1",
                 tags: {} = None,
                 threads: int = 1,
                 population_fetcher: PopulationFetcher = None):
        self._ranges: [] = [600, 1200, 1800, 3600]
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
            logger.debug(f"Getting city boundary for: {city_name}")
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
                    logger.debug(
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

    def _postprocess_cities_data(self, isochrones: [], points: [], ranges,
                                 clip_region):
        gdf = GeoDataFrame()
        boundary = GeoDataFrame.from_features(clip_region)
        boundary = boundary.set_crs(epsg=3857)

        for tag in isochrones:
            for feature in isochrones[tag]:
                if len(feature.values()) <= 0:
                    continue
                if gdf.empty:
                    gdf = GeoDataFrame.from_features(feature)
                    gdf['tag1'] = tag

                else:
                    gdf = gdf.append(GeoDataFrame.from_features(feature))
                    gdf['tag1'] = gdf['tag1'].fillna(tag)
        if not gdf.empty:
            gdf['range'] = gdf['value']
            gdf['tag'] = gdf['tag1']
            gdf.range = gdf.range.astype(int)
            gdf = gdf.set_crs(epsg=3857)
            gdf.range = gdf.range.fillna(0)
            gdf = gdf.dissolve(by=['value', 'tag1'])
            gdf = gp.clip(gdf, boundary)
            for geometry in gdf.geometry:
                test = geometry.to_wkt()
                test_pop = self._population_fetcher.get_population_data(test)
                print()
            gdf: GeoDataFrame = gdf.append(GeoDataFrame.from_features(points))
            return gdf

        # TODO: The tag column now represents the correct geometry. Find a way to remain the tag
        # Maybe split them into groups by tag and then merge them in the groups
        else:
            logger.warning(
                "Results were empty. Check the error logs or try another bounding box."
            )

    def _get_cities_data(self, bbox):
        # cities_data = self._get_city_bounds(bbox)
        with open(
                "/home/jules/workspace/University/Unrelevant/data/test_city_data_heidelberg_karlsruhe.json",
                "r") as f:
            cities_data = json.load(f)
        for city in cities_data:
            logger.info(f"Getting POIs and Isochrones for {city}")
            # TODO redo after development
            # pois = self._get_city_pois_by_bpolys(bpolys=json.dumps(cities_data[city]['boundary']))
            # if not len(pois):
            #     logger.info(f"No POIs found for city: {city}. Excluding it from the results.")
            #     cities_data.pop(city)
            #     continue
            # cities_data[city]['pois'] = pois
            # del pois
            # cities_data[city]['isochrones'] = {}
            city_boundary = cities_data[city]['boundary']
            for category in cities_data[city]['pois']:
                # TODO redo after development
                # isochrones = self._process_isochrones(cities_data[city]['pois'][category], threading_description=f"Calculating Isochrones for {city}")
                isochrones = cities_data[city]['isochrones'][category]
                isochrones = self._postprocess_cities_data(
                    isochrones,
                    cities_data[city]['pois'][category],
                    self._ranges,
                    clip_region=city_boundary)
                cities_data[city]['isochrones'][category] = isochrones
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
        print("")
