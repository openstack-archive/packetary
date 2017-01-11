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

from packetary.api import loaders

from packetary.tests import base
from packetary.tests.stubs import generator


class TestDataLoaders(base.TestCase):
    def test_load_filter(self):
        filter_data = [
            {"name": "p1", "group": "g1"},
            {"name": "p2"},
            {"group": "g3"},
            {"name": "/^.5/", "group": "/^.*3/"},
            {"group": "/^.*4/"},
        ]
        filters = loaders.load_filters(filter_data)
        cases = [
            (True, (generator.gen_package(name='p1', group='g1'),)),
            (True, (generator.gen_package(name="p2", group="g1"),)),
            (False, (generator.gen_package(name="p3", group="g2"),)),
            (True, (generator.gen_package(name="p4", group="g3"),)),
            (True, (generator.gen_package(name="p5", group="g3"),)),
            (True, (generator.gen_package(name="p6", group="g4"),)),
        ]
        self._check_cases(self.assertIs, cases, filters)
        self.assertFalse(loaders.load_filters([])(cases[0][1][0]))

    def test_load_package_relations(self):
        data = [
            {'name': 'test1'},
            {'name': 'test2', 'versions': ['> 1', '< 3']},
        ]
        expected = [
            str(generator.gen_relation('test1')),
            str(generator.gen_relation('test2', ['<', '3'])),
            str(generator.gen_relation('test2', ['>', '1'])),
        ]
        actual = []
        loaders.load_package_relations(data, lambda x: actual.append(str(x)))
        self.assertItemsEqual(expected, actual)
        actual = []
        loaders.load_package_relations(None, actual.append)
        self.assertEqual([], actual)

    def test_get_packages_traverse(self):
        data = [{
            'name': 'r1',
            'excludes': [{'name': 'p1'}]
        }]
        repo = generator.gen_repository(name='r1')
        repo2 = generator.gen_repository(name='r2')
        packages = [
            generator.gen_package(name='p1', version=1, repository=repo),
            generator.gen_package(name='p2', version=2, repository=repo),
            generator.gen_package(name='p3', version=2, repository=repo2),
            generator.gen_package(name='p4', version=2, repository=repo2)
        ]
        actual = []
        traverse = loaders.get_packages_traverse(
            data, lambda x: actual.append(str(x))
        )
        for p in packages:
            traverse(p)

        expected = [str(generator.gen_relation('p2', ['=', '2']))]
        self.assertItemsEqual(expected, actual)
