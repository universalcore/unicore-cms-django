#!/bin/bash

pip="${VENV}/bin/pip"
manage="${VENV}/bin/python ${INSTALLDIR}/${REPO}/manage.py"
settings=`find "${INSTALLDIR}/${REPO}/project/" -name "*_settings.py"`
$pip install -r "${INSTALLDIR}/${REPO}/requirements.txt"

cd "${INSTALLDIR}/${REPO}/"
echo "starting post install for $settings"
for s in $settings
do
    echo "migrating $s"
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage syncdb --noinput --no-initial-data --migrate
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage collectstatic --noinput
done
