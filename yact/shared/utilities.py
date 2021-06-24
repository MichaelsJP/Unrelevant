import logging
from shutil import which

from yact.exceptions.DependencyExceptions import DependencyNotFoundError

logger = logging.getLogger(__name__)


def dependency_check(executable: str):
    """
    Check if a cli tool is installed and callable.
    @param executable: Name of the executable.
    """
    if not which(executable):
        raise DependencyNotFoundError(executable)
