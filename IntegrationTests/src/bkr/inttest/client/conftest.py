import pytest


@pytest.fixture(scope='package', autouse=True)
def beaker_client_suite():
    from bkr.inttest.client import setup_package, teardown_package
    setup_package()
    yield
    teardown_package()
