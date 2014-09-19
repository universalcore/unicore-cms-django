pip="${VENV}/bin/pip"
manage="${VENV}/bin/python ${INSTALLDIR}/${REPO}/manage.py"
settings="${INSTALLDIR}/${REPO}/project/*_settings.py"

$pip install "praekelt-python-gitmodel>=0.1.2 django-grappelli<2.6.1"

for s in $settings
do
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage syncdb --noinput --no-initial-data --migrate
    DJANGO_SETTINGS_MODULE="project.$(basename $s .py)" $manage collectstatic --noinput
done
