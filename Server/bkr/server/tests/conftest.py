import pytest


@pytest.fixture(scope='package', autouse=True)
def server_unit_suite():
    from bkr.server.tests import setup_package
    setup_package()
    yield
