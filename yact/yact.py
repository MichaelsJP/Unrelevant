# -*- coding: utf-8 -*-
import argparse
import configparser
import json
import logging
import os
from datetime import datetime

import pkg_resources

__version__ = pkg_resources.get_distribution("yact").version

from yact.YactBase.Provider.HereProvider import HereProvider
from yact.YactBase.Provider.OpenRouteServiceProvider import OpenRouteServiceProvider
from yact.YactBase.Provider.ValhallaProvider import ValhallaProvider
from yact.YactBase.scenarios.RecreationScenario import RecreationScenario, PopulationFetcher
from yact.YactBase.scenarios.BaseScenario import BaseScenario
from yact.YactBase.scenarios.VaccinationScenario import VaccinationScenario
from yact.exceptions.BaseExceptions import ProviderNotImplementedError, ScenarioNotImplementedError
from yact.exceptions.ConfigExceptions import ConfigFileNotFoundError
from yact.shared.utilities import dependency_check

script_path = os.path.dirname(os.path.realpath(__file__))
config = configparser.ConfigParser()

parser = argparse.ArgumentParser(description='yact command line utility')

parser.add_argument('--version', action='version', version=f'{__version__}')

parser.add_argument(
    '-c',
    '--config-file',
    help='Provide a config file to skip the cli configuration.',
    type=str)
args = parser.parse_args()

if args.config_file:
    config.read(args.config_file)
else:
    raise ConfigFileNotFoundError()

log_format = '%(asctime)s  %(module)8s  %(levelname)5s:  %(message)s'
logger = logging.getLogger()

if logger.hasHandlers():
    logger.handlers.clear()

args_dict = vars(args)


def main():
    dependency_check("gdalinfo")

    # Default settings
    provider = config["DEFAULT"].get("Provider")
    scenario = config["DEFAULT"].get("Scenario", fallback="recreation")
    profile = config["DEFAULT"].get("Profile", fallback="car")
    cities = json.loads(config["DEFAULT"].get("Cities"))
    bbox = config["DEFAULT"].get(
        "Bbox", fallback="8.667398,49.407718,8.719677,49.412392")
    ranges = json.loads(config["DEFAULT"].get(
        "Ranges", fallback="[600, 1200, 1800, 3600]"))
    tags = json.loads(config["DEFAULT"].get("Tags"))
    threads = int(config["DEFAULT"].get("Threads", fallback="2"))
    range_type = config["DEFAULT"].get("Range_Type", fallback="time")
    verbosity = config["DEFAULT"].get("Verbosity", fallback="info")
    output_folder = config["DEFAULT"].get("Output_Folder")

    # Get database settings
    database_url = config['postgres'].get("URL")
    port = config['postgres'].get("Port")
    user = config['postgres'].get("User")
    password = config['postgres'].get("Password")
    database = config['postgres'].get("Database")

    # Logger settings
    formatter = logging.Formatter(fmt=log_format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(config["DEFAULT"].get("Verbosity",
                                          fallback="info").upper())
    logger.addHandler(handler)

    # Ohsome settings
    ohsome_api = config["ohsome"].get("URL", fallback="https://api.ohsome.org")

    # Get provider settings
    if str(provider).lower() == 'ors':
        api_key = config["openrouteservice"].get("Api_Key")
        base_url = config["openrouteservice"].get("URL")
        provider = OpenRouteServiceProvider(
            api_key=api_key,
            profile=profile,
            base_url=base_url if len(base_url) > 0 else None)
    elif str(provider).lower() == 'valhalla':
        range_type = "time"
        api_key = config["Valhalla"].get("Api_Key")
        base_url = config["Valhalla"].get("URL")
        provider = ValhallaProvider(
            api_key=api_key,
            profile=profile,
            base_url=base_url if len(base_url) > 0 else None)
    elif str(provider).lower() == 'here':
        api_key = config["Here"].get("Api_Key")
        provider = HereProvider(api_key=api_key, profile=profile)
    else:
        raise ProviderNotImplementedError(str(provider))

    # Get scenario settings
    if str(scenario).lower() == 'recreation':
        population_fetcher = PopulationFetcher(url=database_url,
                                               port=port,
                                               db=database,
                                               user=user,
                                               password=password)
        scenario = RecreationScenario(cities=cities,
                                      tags=tags,
                                      ranges=ranges,
                                      provider=provider,
                                      ohsome_api=ohsome_api,
                                      threads=threads,
                                      population_fetcher=population_fetcher)
    else:
        raise ScenarioNotImplementedError(str(scenario))

    start = datetime.now()
    logger.info("#######Started processing#######")
    logger.info(f"# Start time: {start}")
    logger.info(f"# Provider: {provider.provider_name}")
    logger.info(f"# Scenario: {scenario.scenario_name}")
    logger.info(f"# Profile: {profile}")
    logger.info(f"# Cities: {cities}")
    logger.info(f"# Ranges: {ranges}")
    logger.info(f"# Range Type: {range_type}")
    logger.info(f"# Verbosity: {verbosity}")
    logger.info(f"# Output Folder: {os.path.abspath(output_folder)}")
    logger.info("#######Started processing#######")

    output_files = process(scenario=scenario, output_folder=output_folder)

    finish = datetime.now()
    logger.info("#######Finisched processing#######")
    logger.info(f"# End time: {finish}")
    logger.info(f"# Elapsed time: {finish - start}")
    logger.info(f"# Output Files:")
    [logger.info(f"# {file}") for file in output_files]
    logger.info("#######Finisched processing#######")


def process(scenario: BaseScenario,
            output_folder: str) -> [str]:  # pragma: no cover
    scenario.process()
    files = scenario.write_results(output_path=output_folder, )
    return files


if __name__ == '__main__':  # pragma: no cover
    main()
