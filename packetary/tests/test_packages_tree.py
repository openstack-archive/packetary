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

from packetary.objects import PackagesTree
from packetary.objects import VersionRange
from packetary.tests import base
from packetary.tests.stubs import generator


class TestPackagesTree(base.TestCase):
    def test_add(self):
        tree = PackagesTree()
        pkg = generator.gen_package(version=1, mandatory=True)
        tree.add(pkg)
        self.assertIs(pkg, tree.find(pkg.name, VersionRange('=', pkg.version)))
        self.assertIs(
            pkg.obsoletes[0],
            tree.obsoletes[pkg.obsoletes[0].name][(pkg.name, pkg.version)]
        )
        self.assertIs(
            pkg.provides[0],
            tree.provides[pkg.provides[0].name][(pkg.name, pkg.version)]
        )
        tree.add(generator.gen_package(version=1, mandatory=False))
        self.assertItemsEqual([pkg], tree.mandatory_packages)

    def test_find_package(self):
        tree = PackagesTree()
        p1 = generator.gen_package(idx=1, version=1)
        p2 = generator.gen_package(idx=1, version=2)
        tree.add(p1)
        tree.add(p2)

        self.assertIs(p1, tree.find(p1.name, VersionRange("<", p2.version)))
        self.assertIs(p2, tree.find(p1.name, VersionRange(">=", p1.version)))
        self.assertIsNone(tree.find(p1.name, VersionRange(">", p2.version)))

    def test_find_obsolete(self):
        tree = PackagesTree()
        p1 = generator.gen_package(
            version=1, obsoletes=[generator.gen_relation('obsolete', ('<', 2))]
        )
        p2 = generator.gen_package(
            version=2, obsoletes=[generator.gen_relation('obsolete', ('<', 2))]
        )
        tree.add(p1)
        tree.add(p2)

        self.assertEqual(
            [p1, p2], tree.find_all("obsolete", VersionRange("<=", 2))
        )
        self.assertIsNone(
            tree.find("obsolete", VersionRange(">", 2))
        )

    def test_find_provides(self):
        tree = PackagesTree()
        p1 = generator.gen_package(
            version=1, obsoletes=[generator.gen_relation('provide', ('<', 2))]
        )
        tree.add(p1)

        self.assertIs(
            p1, tree.find("provide", VersionRange("<=", 2))
        )
        self.assertIsNone(
            tree.find("provide", VersionRange(">", 2))
        )

    def test_get_unresolved_dependencies(self):
        tree = PackagesTree()
        tree.add(generator.gen_package(
            1, requires=[generator.gen_relation("unresolved")]))
        tree.add(generator.gen_package(2, requires=None))
        tree.add(generator.gen_package(
            3, requires=[generator.gen_relation("package1")]
        ))
        unresolved = tree.get_unresolved_dependencies()
        self.assertItemsEqual(
            ["unresolved"],
            (x.name for x in unresolved)
        )
