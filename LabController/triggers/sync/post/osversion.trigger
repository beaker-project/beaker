#!/bin/sh

mkdir osversion_data
beaker-osversion --test-output-dir=./osversion_data $*
