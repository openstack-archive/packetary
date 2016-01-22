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

from packetary.objects.packages_tree import PackagesTree


logger = logging.getLogger(__package__)


class PackagesForest(object):
    """Helper class to deal with dependency graph."""

    def __init__(self):
        self.trees = []

    def add_tree(self):
        """Add new tree to end of forest.

        :return: The added tree
        """
        tree = PackagesTree()
        self.trees.append(tree)
        return tree

    def get_packages(self, requirements, include_mandatory=False):
        """Get the packages according requirements.

        :param requirements: the list of requirements
        :param include_mandatory: if true, the mandatory packages will be
                                  included to result
        :return list of packages to copy
        """

        # TODO(bgaifullin): use versions intersection instead of union
        # now the all versions that fit requirements are selected
        # need to select only one version that fits all requirements

        resolved = set()
        unresolved = set()
        stack = [requirements]

        if include_mandatory:
            for tree in self.trees:
                for mandatory in tree.mandatory_packages:
                    resolved.add(mandatory)
                    stack.append(mandatory.requires)

        while stack:
            requirements = stack.pop()
            for required in requirements:
                for rel in required:
                    if rel not in unresolved:
                        candidate = self.find(rel)
                        if candidate is not None:
                            if candidate not in resolved:
                                stack.append(candidate.requires)
                                resolved.add(candidate)
                            break
                else:
                    unresolved.add(required)
                    logger.warning("Unresolved relation: %s", required)
        return resolved

    def find(self, relation):
        """Finds package in forest.

        :param relation: the package relation
        :return: the packages from first tree if found otherwise empty list
        """
        for tree in self.trees:
            candidate = tree.find(relation.name, relation.version)
            if candidate is not None:
                return candidate
