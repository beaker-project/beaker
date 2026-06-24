import pytest


@pytest.fixture(scope='package', autouse=True)
def labcontroller_suite():
    from bkr.inttest.labcontroller import setup_package, teardown_package
    setup_package()
    yield
    teardown_package()
