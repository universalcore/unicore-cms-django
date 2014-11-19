#!/bin/bash

# halt on any error
set -e

manage="/var/praekelt/bin/python /var/praekelt/unicore-cms-django/manage.py"
settings="/var/praekelt/unicore-cms-django/project/*_settings.py"

for s in $settings
do
    echo "Fixing locales for $s"
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage fix_incorrect_locales
done
