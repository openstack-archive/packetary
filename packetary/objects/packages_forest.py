# -*- coding: utf-8 -*-

#    Copyright 2016 Mirantis, Inc.
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

import logging
import six

from collections import OrderedDict
from packetary.objects.packages_tree import PackagesTree


logger = logging.getLogger(__package__)


class PackagesForest(object):
    """Helper class to deal with dependency graph."""

    def __init__(self):
        self.trees = OrderedDict()

    def add_tree(self, priority):
        """Add new tree to end of forest.

        :return: The added tree
        """

        try:
            return self.trees[priority]
        except KeyError:
            tree = self.trees[priority] = PackagesTree()
            return tree

    def get_packages(self, requirements):
        """Get the packages according requirements.

        :param requirements: the list of requirements
        :return list of packages to copy
        """

        # TODO(bgaifullin): use versions intersection instead of union
        # now the all versions that fit requirements are selected
        # need to select only one version that fits all requirements

        resolved = set()
        unresolved = set()
        stack = [(None, requirements)]

        while stack:
            pkg, requirements = stack.pop()
            for required in requirements:
                for rel in required:
                    if rel not in unresolved:
                        candidate = self.find(rel)
                        if candidate is not None:
                            if candidate not in resolved:
                                stack.append((candidate, candidate.requires))
                                resolved.add(candidate)
                            break
                else:
                    unresolved.add(required)
                    logger.warning("Unresolved relation: %s from %s",
                                   required, pkg and pkg.name)
        return resolved

    def find(self, relation):
        """Finds package in forest.

        :param relation: the package relation
        :return: the packages from first tree if found otherwise empty list
        """
        for tree in six.itervalues(self.trees):
            candidate = tree.find(relation.name, relation.version)
            if candidate is not None:
                return candidate
