# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from collections import defaultdict

import six

from packetary.objects.index import Index
from packetary.objects.package_relation import VersionRange


class PackagesTree(object):
    """Helper class to deal with dependency graph."""

    def __init__(self):
        super(PackagesTree, self).__init__()
        self.mandatory_packages = []
        self.packages = Index()
        self.provides = defaultdict(dict)
        self.obsoletes = defaultdict(dict)

    def add(self, package):
        # store all mandatory packages in separated list for quick access
        if package.mandatory:
            self.mandatory_packages.append(package)

        self.packages.add(package)
        key = package.name, package.version

        for obsolete in package.obsoletes:
            self.obsoletes[obsolete.name][key] = obsolete

        for provide in package.provides:
            self.provides[provide.name][key] = provide

    def find(self, name, version_range):
        """Finds the package by name and range of versions.

        :param name: the package`s name.
        :param version_range: the range of versions.
        :return: the package if it is found, otherwise None
        """
        candidates = self.find_all(name, version_range)
        if len(candidates) > 0:
            return candidates[-1]
        return None

    def find_all(self, name, version_range):
        """Finds the packages by name and range of versions.

        :param name: the package`s name.
        :param version_range: the range of versions.
        :return: the list of suitable packages
        """
        if name in self.packages:
            candidates = self.packages.find_all(name, version_range)
            if len(candidates) > 0:
                return candidates

        if name in self.obsoletes:
            return self._resolve_relation(self.obsoletes[name], version_range)

        if name in self.provides:
            return self._resolve_relation(self.provides[name], version_range)
        return []

    def get_unresolved_dependencies(self):
        """Gets the set of unresolved dependencies.

        :return: the set of unresolved depends.
        """
        unresolved = set()

        for pkg in self.packages:
            for required in pkg.requires:
                for rel in required:
                    if rel not in unresolved:
                        if self.find(rel.name, rel.version) is not None:
                            break
                else:
                    unresolved.add(required)
        return unresolved

    def _resolve_relation(self, relations, version_range):
        """Resolve relation according to relations index.

        :param relations: the index of relations
        :param version_range: the range of versions
        :return: package if found, otherwise None
        """
        result = []
        for key, candidate in six.iteritems(relations):
            if version_range.has_intersection(candidate.version):
                result.extend(
                    self.packages.find_all(key[0], VersionRange('=', key[1]))
                )
        result.sort(key=lambda x: x.version)
        return result
