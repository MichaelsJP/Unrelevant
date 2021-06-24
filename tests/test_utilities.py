import pytest

from yact.exceptions.DependencyExceptions import DependencyNotFoundError
from yact.shared.utilities import dependency_check


@pytest.mark.parametrize('dependency', ["sh", "watch"])
def test_test_for_dependency(dependency):
    dependency_check(dependency)


@pytest.mark.parametrize('dependency', ["aadsfwer", "fadsadsf"])
def test_dependency_check(dependency):
    with pytest.raises(DependencyNotFoundError):
        dependency_check(dependency)
