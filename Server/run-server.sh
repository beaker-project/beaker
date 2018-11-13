#!/bin/bash

export PYTHONPATH=../Common:.${PYTHONPATH:+:$PYTHONPATH}
exec python2 -c 'import sys, os.path; \
                sys.path[0] = os.path.abspath(sys.path[0]); \
                __requires__ = ["CherryPy < 3.0", "Jinja2 >= 2.6"]; import pkg_resources; \
                from gunicorn.app.wsgiapp import run; run()' \
               --bind :8080 -t 3600 --workers 8 --access-logfile - \
               --preload bkr.server.wsgi:application "$@"
