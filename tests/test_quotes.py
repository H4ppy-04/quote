import pytest

from src import main


def test_zero_quote_diff(quote_diff_duplicate: int):
    assert quote_diff_duplicate == 0


def test_query_identifier(quote_list):
    quote: main.Optional[main.Quote] = main.query_quote(
        quote_list, identifier=0, author=None
    )
    assert isinstance(quote, main.Quote)


@pytest.mark.git
def test_version_exists():
    version = main.get_version()
    assert isinstance(version, str) and version != ""
