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

from bintrees import FastRBTree
from collections import defaultdict
import functools
import operator
import six


def _make_operator(direction, op):
    """Makes search operator from low-level operation and search direction."""
    return functools.partial(direction, condition=op)


def _start_upperbound(versions, version, condition):
    """Gets all versions from [start, version] that meet condition.

    :param versions: the tree of versions.
    :param version: the required version
    :param condition: condition for search
    :return: the list of found versions
    """

    result = list(versions.value_slice(None, version))
    try:
        bound = versions.ceiling_item(version)
        if condition(bound[0], version):
            result.append(bound[1])
    except KeyError:
        pass
    return result


def _lowerbound_end(versions, version, condition):
    """Gets all versions from [version, end] that meet condition.

    :param versions: the tree of versions.
    :param version: the required version
    :param condition: condition for search
    :return: the list of found versions
    """
    result = []
    items = iter(versions.item_slice(version, None))
    bound = next(items, None)
    if bound is None:
        return result
    if condition(bound[0], version):
        result.append(bound[1])
    result.extend(x[1] for x in items)
    return result


def _equal(versions, version):
    """Gets the package with specified version.

    :param versions: the tree of versions.
    :param version: the required version
    """
    value = versions.get(version, None)
    return [] if value is None else [value]


def _any(versions, _):
    """Gets the package with max version.

    :param versions: the tree of versions.
    """
    return list(versions.values())


class Index(object):
    """The search index for packages.

    Builds three search-indexes:
    - index of packages with versions.
    - index of virtual packages (provides).
    - index of obsoleted packages (obsoletes).

    Uses to find package by name and range of versions.
    """

    operators = {
        None: _any,
        "<": _make_operator(_start_upperbound, operator.lt),
        "<=": _make_operator(_start_upperbound, operator.le),
        ">": _make_operator(_lowerbound_end, operator.gt),
        ">=": _make_operator(_lowerbound_end, operator.ge),
        "=": _equal,
    }

    def __init__(self):
        self.packages = defaultdict(FastRBTree)

    def __iter__(self):
        """Iterates over all packages including versions."""
        return self.get_all()

    def __len__(self, _reduce=six.functools.reduce):
        """Returns the total number of packages with versions."""
        return _reduce(
            lambda x, y: x + len(y),
            six.itervalues(self.packages),
            0
        )

    def __contains__(self, name):
        """Checks that index contains any package with such name."""
        return name in self.packages

    def get_all(self):
        """Gets sequence from all of packages including versions."""

        for versions in six.itervalues(self.packages):
            for version in versions.values():
                yield version

    def find_all(self, name, version_range):
        """Finds the packages by name and range of versions.

        :param name: the package`s name.
        :param version_range: the range of versions.
        :return: the list of suitable packages
        """
        if name in self.packages:
            return self._find_versions(self.packages[name], version_range)
        return []

    def add(self, package):
        """Adds new package to indexes.

        :param package: the package object.
        """
        self.packages[package.name][package.version] = package

    @staticmethod
    def _find_versions(versions, version_range):
        """Searches accurate version.

        Search for the highest version out of intersection
        of existing and required range of versions.

        :param versions: the existing versions
        :param version_range: the required range of versions
        :return: package if found, otherwise None
        """

        try:
            op = Index.operators[version_range.op]
        except KeyError:
            raise ValueError(
                "Unsupported operation: {0}"
                .format(version_range.op)
            )
        return op(versions, version_range.edge)
