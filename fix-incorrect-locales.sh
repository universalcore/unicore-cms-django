#!/bin/bash

settings="project/*_settings.py"

for s in $settings
do
    echo "Fixing locales for $s"
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" ./manage.py fix_incorrect_locales
done
