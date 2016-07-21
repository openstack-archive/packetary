..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Build packages from src
=======================

https://blueprints.launchpad.net/packetary/+spec/build-packages

Implement package building module in Packetary to provide single application to
solve full range of tasks of packaging and repositories management.


--------------------
Problem description
--------------------

Repository management and packets/packages building is
held in different interfaces that take a long time.
It is more convenient to build packages using the same interface.

----------------
Proposed changes
----------------

We propose to implement building scripts to integrate it in
the Packetary and provide a Python application that wraps the
process to create a rpm and deb packages, relying on Mock to build rpm
packages and Sbuild to build deb packages in isolated environment.



------------
Alternatives
------------

* Koji:
  Supports rpm based distributions only
  https://fedoraproject.org/wiki/Koji

* Automated build farm (ABF):
  Supports rpm based distributions only
  http://www.rosalab.ru/products/rosa_abf
  https://abf.io/

* Delorean
  Supports rpm based distributions only
  Supports python packages only
  Requires separate docker image for each supported distribution
  https://github.com/openstack-packages/delorean

* docker-rpm-builder
  Supports rpm based distributions only
  Requires separate docker image for each supported distribution
  https://github.com/alanfranz/docker-rpm-builder

--------------
Implementation
--------------


*     Use standard upstream Linux distro tools to build packages (mock, sbuild)

*     Every package should be built in a clean and up-to-date buildroot.

*     Package build tool is able to run build stage for different revisions
      of the same package in parallel on the same host.

*     Packages are built from git repositories with unpacked source
      (it's not necessary to commit source tarballs into git).

Packager should support following source layouts:

- Source rpm file (.src.rpm)

- Standard source layout (git project):


  ./source tarball (.tar.*z)

  ./rpm specfile (.spec)

  ./other files related to package (.patch .init etc)


Shell command:

.. code-block:: bash

    packetary build --repo-config repos.yaml \
                    --packages-config packages.yaml \
                    --output ./dest

Format of repos.yaml and packages.yaml provided below

Repo.yaml format:

.. code-block:: yaml

    rpm:
      - name: repo-name
        uri: http://mirrors.fedoraproject.org/mirrorlist?repo=epel-5&arch=i386

      - name: another-repo-name
        uri: http://fedoraproject.org/repos/dist-5E-epel-build/latest/i386/

    deb:
      - name: example
        type: deb
        uri: http://site.example.com/debian
        suite: trusty
        section:
          - main
          - restricted

      - name: example
        type: deb-src
        uri: http://site.example.com/debian
        suite: trusty
        section:
          - main
          - restricted

Packages YAML format:

.. code-block:: yaml

     - source: /home/arno/projects/mirantis/mock-sandbox/zeromq
       release: centos-7-x86_64

     - source: /home/arno/projects/mirantis/mock-sandbox/zeromq
       release: centos-7-x86_64



Assignee(s)
===========

Primary assignee:
  Ivan Bogomazov <ibogomazov@mirantis.com>

Other contributors:
  None

Mandatory design review:
  None


Work Items
==========

* Write rpm-build packetary driver, which wrapping system mock-build

* Write deb-build packetary driver, which wrapping system sbuild

* Write tool to update build chroot package manager configs

* Implement YAML based interface, to be able to mass build packages



Dependencies
============

None

----------
References
----------
https://fedoraproject.org/wiki/Mock
https://wiki.debian.org/sbuild
