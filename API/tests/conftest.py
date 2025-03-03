import pytest
from bkr.app import create_app

app = create_app()

@pytest.fixture()
def client():
    with app.test_client() as c:
        yield c


@pytest.fixture()
def runner():
    return app.test_cli_runner()
