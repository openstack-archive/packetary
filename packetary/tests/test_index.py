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

import six

from packetary.objects.index import Index

from packetary import objects
from packetary.tests import base
from packetary.tests.stubs.generator import gen_package


class TestIndex(base.TestCase):
    def test_add(self):
        index = Index()
        package1 = gen_package(version=1)
        index.add(package1)
        self.assertIn(package1.name, index.packages)
        self.assertEqual(
            [(1, package1)],
            list(index.packages[package1.name].items())
        )

        package2 = gen_package(version=2)
        index.add(package2)
        self.assertEqual(1, len(index.packages))
        self.assertEqual(
            [(1, package1), (2, package2)],
            list(index.packages[package1.name].items())
        )

    def test_find_top_down(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)
        self.assertEqual(
            [p1, p2],
            index.find_all(p1.name, objects.VersionRange("<=", 2))
        )
        self.assertEqual(
            [p1],
            index.find_all(p1.name, objects.VersionRange("<", 2))
        )
        self.assertEqual(
            [],
            index.find_all(p1.name, objects.VersionRange("<", 1))
        )

    def test_find_down_up(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)
        self.assertEqual(
            [p2],
            index.find_all(p1.name, objects.VersionRange(">=", 2))
        )
        self.assertEqual(
            [p2],
            index.find_all(p1.name, objects.VersionRange(">", 1))
        )
        self.assertEqual(
            [],
            index.find_all(p1.name, objects.VersionRange(">", 2))
        )

    def test_find_with_specified_version(self):
        index = Index()
        p1 = gen_package(idx=1, version=1)
        p2 = gen_package(idx=1, version=2)
        index.add(p1)
        index.add(p2)

        self.assertItemsEqual(
            [p1],
            index.find_all(p1.name, objects.VersionRange("=", p1.version))
        )
        self.assertItemsEqual(
            [p2],
            index.find_all(p2.name, objects.VersionRange("=", p2.version))
        )

    def test_len(self):
        index = Index()
        for i in six.moves.range(3):
            index.add(gen_package(idx=i + 1))
        self.assertEqual(3, len(index))

        for i in six.moves.range(3):
            index.add(gen_package(idx=i + 1, version=2))
        self.assertEqual(6, len(index))
        self.assertEqual(3, len(index.packages))

        for i in six.moves.range(3):
            index.add(gen_package(idx=i + 1, version=2))
        self.assertEqual(6, len(index))
        self.assertEqual(3, len(index.packages))
