====================
Repository structure
====================

* debian
  Specs for DEB packages.

* doc
  Documentation for packetary module.

* packetary
  Package provides object model and API for dealing with deb
  and rpm repositories. One can use this framework to
  implement operations like building repository
  from a set of packages, clone repository, find package
  dependencies, mix repositories, pull out a subset of
  packages into a separate repository, etc.

  Features:
  * Common interface for different package-managers.
  * Utility to build dependency graph for package(s).
  * Utility to create mirror of repository according to dependency graph.

* specs
  Specs for RPM packages.
