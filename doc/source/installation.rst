============
Installation
============
Install system requirements::

    ~ $ sudo aptitude install yum \
        yum-utils \
        createrepo \
        mock \
        sbuild \
        git \
        libxml2-dev \
        libxslt1-dev \
        python-dev \
        python-virtualenv \
        zlib1g-dev

Install from sources::

    ~ $ git clone https://git.openstack.org/openstack/packetary
    ~ $ cd packetary/
    ~/packetary$ virtualenv .venv
    ~/packetary$ source .venv/bin/activate
    ~/packetary$ pip install -r requirements.txt
    ~/packetary$ python setup.py install
