import pytest


@pytest.fixture(scope='session', autouse=True)
def beaker_suite():
    from bkr.inttest import setup_package, teardown_package
    setup_package()
    yield
    teardown_package()
