Unicore CMS Django
==================

This is one to throw away.

Install on OSX
--------------

Install libffi & libgit with brew.

    $ brew install libffi
    $ brew install libgit2

Install the packages in a virtualenv with pip.

    $ virtualenv ve
    $ source ve/bin/activate
    (ve)$ pip install cffi==0.8.6
    (ve)$ pip install pygit2==0.20.3
    (ve)$ pip install -e .
