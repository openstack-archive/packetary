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
        self.assertIs(RPM_PACKAGING_SCHEMA, self.driver.get_data_schema())

    def get_for_caching(self):
        data = {'src': '/src', 'rpm': {'spec': '/spec'}}
        self.assertEqual(['/src', '/spec'], self.driver.get_for_caching(data))

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
        data = {'src': '/src', 'rpm': {'spec': '/spec', 'options': {'a': '1'}}}
        cache = {'/src': '/src', '/spec': '/spec'}
        with mock.patch.object(self.driver, '_invoke_mock') as call_mock:
            self.driver.build_packages(data, cache, '/tmp', packages.append)

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
                'buildsrpm', resultdir=tmpdir, spec='/spec',
                sources='/src', a='1'
            ),
            mock.call('rebuild', expected_packages[0], resultdir=tmpdir, a='1')
        ])
        utils_mock.move_files.assert_has_calls(
            [mock.call(tmpdir, '/tmp/SRPM', '*.src.rpm'),
             mock.call(tmpdir, '/tmp/RPM', '*.rpm')]
        )

    @mock.patch('packetary.drivers.mock_driver.subprocess')
    def test_invoke_mock(self, subprocess_mock):
        with mock.patch.object(self.driver, '_assemble_cmdline') as _assemble:
            self.driver._invoke_mock('cmd', 'arg', key1='1')
            _assemble.assert_called_once_with('cmd', ('arg', ), {'key1': '1'})
            subprocess_mock.check_call.assert_called_once_with(
                _assemble.return_value
            )

    def test_assemble_cmdline(self):
        self.assertEqual(
            [
                '/bin/mock', '--root', 'default', '--configdir', '/etc/mock',
                '--src', '/src', '--rebuild', 'package1'
            ],
            self.driver._assemble_cmdline(
                'rebuild', ('package1',), {'src': '/src'}
            )
        )
        self.driver.config_dir = None
        self.assertEqual(
            ['/bin/mock', '--root', 'default', '--src', '/src', '--build'],
            self.driver._assemble_cmdline('build', (), {'src': '/src'})
        )
        self.driver.config_name = None
        self.assertEqual(
            ['/bin/mock', '--src', 'src1', '--src', 'src2', '--build'],
            self.driver._assemble_cmdline(
                'build', (), {'src': ['src1', 'src2']}
            )
        )
