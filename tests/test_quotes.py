import pytest
from src import main


@pytest.mark.git
def test_version_exists():
    version = main.get_version()
    assert isinstance(version, str) and version != ""
