# -*- coding: utf-8 -*-
import argparse
import logging
import os
from datetime import datetime

import pkg_resources

__version__ = pkg_resources.get_distribution("yact").version

from yact.YactBase.Provider.HereProvider import HereProvider
from yact.YactBase.Provider.OpenRouteServiceProvider import OpenRouteServiceProvider
from yact.YactBase.Provider.ValhallaProvider import ValhallaProvider
from yact.YactBase.scenarios.RecreationScenario import RecreationScenario
from yact.YactBase.scenarios.BaseScenario import BaseScenario
from yact.YactBase.scenarios.VaccinationScenario import VaccinationScenario
from yact.exceptions.BaseExceptions import ProviderNotImplementedError, ScenarioNotImplementedError
from yact.shared.utilities import dependency_check

LOGGER = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='yact command line utility')

parser.add_argument('--version', action='version', version=f'{__version__}')

parser.add_argument('outputFolder',
                    help='Provide the folder path where to write results.',
                    type=str)

parser.add_argument(
    '-s',
    '--scenario',
    help='Provide the scenario to calculate. Default: recreation',
    choices=['vaccination, recreation'],
    type=str,
    default="recreation")

parser.add_argument(
    '-p',
    '--provider',
    help='Provide the provider to calculate the results with. Default: ors',
    choices=['ors', 'valhalla', 'here'],
    type=str,
    default="ors")

parser.add_argument(
    '-f',
    '--profile',
    help=
    'Provide the provider profile for the routing calculations. Default: car',
    choices=['car', 'pedestrian'],
    type=str,
    default="car")

parser.add_argument('-k',
                    '--apikey',
                    help='Provide the provider API key. Example: "1234987234"',
                    type=str)

parser.add_argument(
    '-b',
    '--bbox',
    help=
    'Provide a bounding box to query the scenarios for. Default: "8.67066,49.41423,8.68177,49.4204"',
    type=str,
    default="8.667398,49.407718,8.719677,49.412392")

parser.add_argument(
    '-r',
    '--ranges',
    help='Provide ranges for the isochrones in seconds. Default: 100',
    default=[100],
    nargs='+',
    type=int)

parser.add_argument(
    '-t',
    '--rangetype',
    help=
    'Provide the range type for isochrones. For valhalla only time is valid. Default: "time"',
    choices=["time", "distance"],
    type=str,
    default="time")

parser.add_argument('-v',
                    '--verbosity',
                    help="Choose logging verbosity. Default: info",
                    choices=['debug', 'info'],
                    default='info',
                    type=str)

args = parser.parse_args()

log_format = '%(asctime)s  %(module)8s  %(levelname)5s:  %(message)s'
logging.basicConfig(level=args.verbosity.upper(), format=log_format)

args_dict = vars(args)


def main():
    dependency_check("gdalinfo")

    output_folder = args.outputFolder
    api_key = args.apikey
    profile = args.profile
    bbox = args.bbox
    ranges = args.ranges
    range_type = args.rangetype
    verbosity = args.verbosity

    provider = OpenRouteServiceProvider
    if str(args.provider).lower() == 'ors':
        provider = OpenRouteServiceProvider(api_key=api_key, profile=profile)
    elif str(args.provider).lower() == 'valhalla':
        range_type = "time"
        provider = ValhallaProvider(api_key=api_key, profile=profile)
    elif str(args.provider).lower() == 'here':
        provider = HereProvider(api_key=api_key, profile=profile)
    else:
        raise ProviderNotImplementedError(str(args.provider))

    scenario = VaccinationScenario
    if str(args.scenario).lower() == 'vaccination':
        scenario = VaccinationScenario(provider=provider,
                                       ranges=ranges,
                                       range_type=range_type)
    elif str(args.scenario).lower() == 'recreation':
        scenario = RecreationScenario(provider=provider)
    else:
        raise ScenarioNotImplementedError(str(args.scenario))

    start = datetime.now()
    print_ranges = str(ranges).strip('[').strip(']').replace(',', ' ')
    LOGGER.info("#######Started processing#######")
    LOGGER.info(
        f"# Run command: yact {output_folder} -v {verbosity} -s {scenario.scenario_name} -p {provider.provider_name} -f {profile} -r {print_ranges} -t {range_type} -b {bbox} -k  ***"
    )
    LOGGER.info(f"# Start time: {start}")
    LOGGER.info(f"# Provider: {provider.provider_name}")
    LOGGER.info(f"# Scenario: {scenario.scenario_name}")
    LOGGER.info(f"# Output Folder: {os.path.abspath(output_folder)}")
    LOGGER.info("################################")

    output_files = process(scenario=scenario,
                           output_folder=output_folder,
                           bbox=bbox)

    finish = datetime.now()
    LOGGER.info("#######Finisched processing#######")
    LOGGER.info(f"# End time: {finish}")
    LOGGER.info(f"# Elapsed time: {finish - start}")
    LOGGER.info(f"# Output Files:")
    [LOGGER.info(f"# {file}") for file in output_files]
    LOGGER.info("#######Finisched processing#######")


def process(scenario: BaseScenario, output_folder: str,
            bbox: str) -> [str]:  # pragma: no cover
    scenario.process(bbox)
    files = scenario.write_results(output_path=output_folder, )
    return files


if __name__ == '__main__':  # pragma: no cover
    main()
