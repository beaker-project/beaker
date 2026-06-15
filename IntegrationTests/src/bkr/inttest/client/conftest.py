import os
import pytest


@pytest.fixture(scope='package', autouse=True)
def beaker_client_suite():
    from bkr.inttest.client import setup_package, teardown_package
    setup_package()
    yield
    teardown_package()


def pytest_configure(config):
    config.addinivalue_line('markers',
            'xmlrpc: test exercises the XML-RPC endpoint')


def pytest_collection_modifyitems(config, items):
    if os.environ.get('BKR_PY3') != '1':
        return
    skip = pytest.mark.skip(reason='XML-RPC endpoint is not served by wsgi_py3')
    for item in items:
        if item.get_closest_marker('xmlrpc'):
            item.add_marker(skip)
