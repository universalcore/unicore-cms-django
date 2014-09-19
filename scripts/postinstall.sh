manage="${VENV}/bin/python ${INSTALLDIR}/${REPO}/manage.py"
settings="${INSTALLDIR}/${REPO}/project/*_settings.py"

for s in $settings
do
    DJANGO_SETTINGS_MODULE='project."$(basename $s .py)"' $manage syncdb --noinput --no-initial-data --migrate
    DJANGO_SETTINGS_MODULE='project."$(basename $s .py)"' $manage collectstatic --noinput
done
