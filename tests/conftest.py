import pytest

from src import main


@pytest.mark.git
def test_version_exists():
    version = main.get_version()
    assert isinstance(version, str) and version != ""


@pytest.fixture
def quote_hashmap() -> dict:
    return main.read_json(file="tests/data/quotes.json")


@pytest.fixture
def quote_list() -> list[main.Quote]:
    return main.load_quotes(file="tests/data/quotes.json")


@pytest.fixture
def quote_diff_duplicate(quote_list, quote_hashmap) -> int:
    return main.get_quote_diff(quote_list, quote_hashmap)
