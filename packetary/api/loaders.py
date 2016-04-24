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

import re

import six

from packetary.objects.package_relation import PackageRelation


def make_pattern_match(name, value):
    return lambda o: re.match(value, getattr(o, name))


def make_exact_match(name, value):
    return lambda o: getattr(o, name) == value


def make_attr_match(name, value):
    if value.startswith('/') and value.endswith('/'):
        return make_pattern_match(name, value[1:-1])
    return make_exact_match(name, value)


def all_of(operators):
    return lambda o: all((x(o) for x in operators))


def any_of(operators):
    return lambda o: any((f(o) for f in operators))


def load_filters(data):
    """Loads filter from filter data.

    Property value could be a string or a python regexp.
    Example of filters data:
    - name: full-package-name
      section: section1
    - name: /^.*substr/

    :param data:  A list of filters
    :return: Lambda that could match a particular package.
    """
    return any_of([
        all_of([make_attr_match(n, v) for n, v in six.iteritems(attrs)])
        for attrs in data
    ])


def load_package_relations(data, consumer):
    """Gets the list PackageRelations from descriptions.

    :param data: the descriptions of package relations
    :param consumer: the result consumer
    """
    if not data:
        return

    for d in data:
        versions = d.get('versions', None)
        if versions is None:
            consumer(PackageRelation.from_args((d['name'],)))
        else:
            for version in versions:
                consumer(PackageRelation.from_args(
                    ([d['name']] + version.split(None, 1))
                ))


def get_packages_traverse(data, consumer):
    """Gets the traverse to get all packages from repository as relations.

    :param data: the description of repositories to traverse
    :param consumer: the requirements consumer
    :return: callable that expects package as argument
    """
    if not data:
        return lambda _: None

    filters_per_repo = {
        d['name']: load_filters(d.get('excludes', ()))
        for d in data
    }

    def traverse(pkg):
        if pkg.repository.name in filters_per_repo:
            excludes_filter = filters_per_repo[pkg.repository.name]
            if not excludes_filter(pkg):
                consumer(
                    PackageRelation.from_args((pkg.name, '=', pkg.version))
                )
    return traverse
