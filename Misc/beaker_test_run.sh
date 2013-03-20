#!/bin/bash
# This script clones the Beaker develop branch and runs the 
# test suite

# clone beaker
git clone -b develop git://git.beaker-project.org/beaker

# Run the tests
pushd beaker/
make build
cd IntegrationTests
./run-tests.sh
popd
