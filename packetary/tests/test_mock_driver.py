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

import mock

from packetary.drivers import mock_driver
from packetary.schemas import RPM_PACKAGING_SCHEMA

from packetary.tests import base


class TestMockDriver(base.TestCase):
    def setUp(self):
        with mock.patch('packetary.drivers.mock_driver.utils') as u_mock:
            u_mock.find_executable.return_value = '/bin/mock'
            self.driver = mock_driver.MockDriver('/etc/mock/default.cfg')
            self.driver.logger = mock.MagicMock()

    def test_get_data_schema(self):
        self.assertEqual(RPM_PACKAGING_SCHEMA, self.driver.get_data_schema())

    def test_get_section_name(self):
        self.assertEqual('rpm', self.driver.get_section_name())

    def test_get_spec(self):
        self.assertEqual('1', self.driver.get_spec({'spec': '1'}))

    def test_get_options(self):
        self.assertEqual({}, self.driver.get_options({}))
        self.assertEqual(
            {'t': 1}, self.driver.get_options({'options': {'t': 1}})
        )

    @mock.patch('packetary.drivers.mock_driver.utils')
    @mock.patch('packetary.drivers.mock_driver.glob')
    def test_build_packages(self, glob_mock, utils_mock):
        packages = []
        expected_packages = ['/tmp/package1.srpm', '/tmp/package1.rpm']
        utils_mock.move_files.side_effect = [
            expected_packages[:1], expected_packages[1:]
        ]
        glob_mock.iglob.return_value = expected_packages[:1]
        utils_mock.create_tmp_dir().__enter__.return_value = '/tmp'
        with mock.patch.object(self.driver, 'call_mock') as call_mock:
            self.driver.build_packages(
                '/src', '/spec.txt', {'a': 1}, '/tmp', packages.append
            )

        self.assertEqual(expected_packages, packages)
        utils_mock.create_tmp_dir.assert_called_with()
        utils_mock.create_tmp_dir().__enter__.assert_called_once_with()
        utils_mock.create_tmp_dir().__exit__.assert_called_once_with(
            None, None, None
        )

        utils_mock.ensure_dir_exist.assert_has_calls(
            [mock.call('/tmp/SRPM'), mock.call('/tmp/RPM')],
        )
        tmpdir = utils_mock.create_tmp_dir().__enter__()
        call_mock.assert_has_calls([
            mock.call(
                'buildsrpm', resultdir=tmpdir, spec='/spec.txt',
                sources='/src', a=1
            ),
            mock.call('rebuild', expected_packages[0], resultdir=tmpdir, a=1)
        ])
        utils_mock.move_files.assert_has_calls(
            [mock.call(tmpdir, '/tmp/SRPM', '*.src.rpm', True),
             mock.call(tmpdir, '/tmp/RPM', '*.rpm', True)]
        )

    @mock.patch('packetary.drivers.mock_driver.subprocess')
    def test_call_mock(self, subprocess_mock):
        with mock.patch.object(self.driver, 'get_mock_command') as get_mock:
            self.driver.call_mock('cmd', 'arg', key1='1')
            get_mock.assert_called_once_with(
                'cmd', ('arg', ), {'key1': '1'}
            )
            subprocess_mock.check_call.assert_called_once_with(
                get_mock.return_value
            )

    def test_get_mock_command(self):
        self.assertEqual(
            [
                '/bin/mock', '--root', 'default', '--configdir', '/etc/mock',
                '--src', '/src', '--rebuild', 'package1'
            ],
            self.driver.get_mock_command(
                'rebuild', ('package1',), {'src': '/src'}
            )
        )
        self.driver.config_dir = None
        self.assertEqual(
            ['/bin/mock', '--root', 'default', '--src', '/src', '--build'],
            self.driver.get_mock_command('build', (), {'src': '/src'})
        )
        self.driver.config_name = None
        self.assertEqual(
            ['/bin/mock', '--src', 'src1', '--src', 'src2', '--build'],
            self.driver.get_mock_command(
                'build', (), {'src': ['src1', 'src2']}
            )
        )
