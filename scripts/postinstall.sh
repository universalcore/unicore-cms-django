pip="${VENV}/bin/pip"
manage="${VENV}/bin/python ${INSTALLDIR}/${REPO}/manage.py"
settings="${INSTALLDIR}/${REPO}/project/*_settings.py"

$pip install -r "${INSTALLDIR}/${REPO}/requirements.txt"

for s in $settings
do
    echo "migrating $s"
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage syncdb --noinput --no-initial-data --migrate
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage collectstatic --noinput
done
