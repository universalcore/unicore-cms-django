#!/bin/bash

set -e

coverage erase
coverage run `which py.test` --ds=test_settings --verbose cms $1
coverage report
