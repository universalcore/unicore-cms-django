#!/bin/bash

# halt on any error
set -e

mkdir -p unicore/content

touch unicore/__init__.py
touch unicore/content/__init__.py

python -m elasticgit.tools \
    migrate-gitmodel-repo \
    ./project/cmsrepo/ unicore.content.models

python -m elasticgit.tools \
    load-schema ./project/cmsrepo/unicore.content.models/GitPageModel.avro.json \
                ./project/cmsrepo/unicore.content.models/GitCategoryModel.avro.json \
                --map-field uuid=elasticgit.models.UUIDField \
                --rename-model GitPageModel=Page \
                --rename-model GitCategoryModel=Category \
                > ./unicore/content/models.py

mv project/cmsrepo/unicore.content.models/*.avro.json ./unicore/
