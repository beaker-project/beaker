import logging
import sys
import time
from connexion.resolver import RestyResolver
from bkr import config

logger = logging.getLogger(__name__)


def create_app():
    app = config.connex_app
    app.add_api("swagger.yml",  resolver=RestyResolver('bkr.api'))
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)
