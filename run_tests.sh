#!/bin/bash

set -e

flake8 cms --exclude migrations

coverage erase
coverage run `which py.test` --ds=test_settings --verbose cms "$@"
coverage report
