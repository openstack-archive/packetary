========
Usage
========

Build packages with packetary
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build packages::

    ~/packetary$ packetary build --type rpm \
                 --input-data packages.yaml \
                 --output-dir /tmp/rpm/packages

Format of repos.yaml and packages.yaml provided below.

packages.yaml::

    - source: /home/arno/projects/mirantis/mock-sandbox/zeromq
      spec: /home/arno/projects/mirantis/mock-sandbox/zeromq/zeromq.spec
      release: centos-5-x86_64

    - source: /home/arno/projects/mirantis/mock-sandbox/zeromq
      spec: /home/arno/projects/mirantis/mock-sandbox/zeromq/zeromq.spec
      release: centos-7-x86_64


Clone custom repositories
^^^^^^^^^^^^^^^^^^^^^^^^^

Cloning rpm repos::

    packetary clone -t rpm \
                    -r centos_mirror.yaml \
                    -R centos_packages.yaml \
                    -d /tmp/mirror

Clone deb repos::

    packetary clone -t deb \
                    -r ubuntu_mirrors.yaml \
                    -R ubuntu_packages.yaml \
                    -d /tmp/mirror

where:

-t - rpm or deb. In our case we work with rpm repos

-r - mirror(s) list to work with

-R - additional filter that should be applied to repo,
     eg.: clone exact packages, exclude some packages by name
     (for example, debuginfo)

YAML examples below

centos_mirror.yaml::

     - name: "mos-repos"
       uri: "http://mirror.seed-cz1.fuel-infra.org/mos-repos/centos/mos-master-centos7/os/x86_64/"
       priority: 1
       path: "/tmp/mirror/mos-centos"

     - name: "upstream-os"
       uri: http://mirror.centos.org/centos/7/os/x86_64
       priority: 90
       path: "/tmp/mirror/centos"

     - name: "upstream-updates"
       uri: "http://mirror.centos.org/centos/7/updates/x86_64"
       priority: 10
       path: "/tmp/mirror/centos"

     - name: "upstream-extras"
       uri: "http://mirror.centos.org/centos/7/extras/x86_64"
       priority: 90
       path: "/tmp/mirror/centos"

centos_packages.yaml::

    repositories:
        - name: mos-repos
          excludes:
              - name: "/^.*debuginfo.*/"

    packages:
        - name: Cython
        - name: GeoIP
        - name: MySQL-python
        - name: NetworkManager
        - name: NetworkManager-team
        - name: NetworkManager-tui
        - name: PyPAM
        # fuel packages
        - name: fencing-agent
        - name: fuel
        - name: fuel-agent
        - name: fuel-bootstrap-cli
        - name: fuel-ha-utils
        - name: fuel-library
        - name: fuelmenu
        - name: fuel-migrate

ubuntu_packages.yaml::

    # we don't need essential packages from repo
    mandatory: False

    # we don't need debug packages
    repositories:
        - name: "ubuntu"
          excludes:
              - group: "debug"

    packages:
        - name: aodh-api
        - name: aodh-common
        - name: aodh-doc
        - name: aodh-evaluator
        - name: aodh-expirer
        - name: aodh-listener

ubuntu_mirrors.yaml::

    - name: "mos9.0-ubuntu"
      uri: "http://mirror.seed-cz1.fuel-infra.org/mos-repos/ubuntu/9.0/"
      suite: "mos9.0"
      section: ["main", "restricted"]
      priority: 1000
       path: "/tmp/mirrors/ubuntu"
