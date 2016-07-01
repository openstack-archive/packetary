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

import functools
import glob
import os
import subprocess

from packetary.drivers.base import PackagingDriverBase
from packetary.library import utils
from packetary.schemas import RPM_PACKAGING_SCHEMA


class MockDriver(PackagingDriverBase):
    def __init__(self, config_file):
        super(MockDriver, self).__init__()
        self.mock_bin = utils.find_executable('mock')
        if config_file:
            self.config_dir = os.path.dirname(config_file)
            self.config_name = os.path.splitext(
                os.path.basename(config_file)
            )[0]
        else:
            self.config_dir = ''
            self.config_name = ''

    def get_section_name(self):
        return 'rpm'

    def get_data_schema(self):
        return RPM_PACKAGING_SCHEMA

    def get_spec(self, data):
        return data['spec']

    def get_options(self, data):
        return data.get('options') or {}

    def build_packages(self, source, spec, options, output_dir, consumer):
        with utils.create_tmp_dir() as tmpdir:
            self.buildsrpm(
                resultdir=tmpdir, spec=spec, sources=source, **options
            )
            srpms_dir = os.path.join(output_dir, 'SRPM')
            utils.ensure_dir_exist(srpms_dir)
            srpms = glob.iglob(os.path.join(srpms_dir, '*.src.rpm'))
            rpms_dir = os.path.join(output_dir, 'RPM')
            utils.ensure_dir_exist(rpms_dir)
            self.rebuild(*srpms, resultdir=tmpdir, **options)

            # rebuild commands rebuilds source rpm too
            # notify only about last version
            for rpm in utils.move_files(tmpdir, srpms_dir, '*.src.rpm', True):
                consumer(rpm)

            for rpm in utils.move_files(tmpdir, rpms_dir, '*.rpm', True):
                consumer(rpm)

    def __getattr__(self, item):
        return functools.partial(self.call_mock, item)

    def call_mock(self, command, *args, **kwargs):
        cmd = self.get_mock_command(command, args, kwargs)
        self.logger.debug("start command: '%'", ' '.join(cmd))
        subprocess.check_call(cmd)

    def get_mock_command(self, command, args, kwargs):
        def add_option(name, value):
            if isinstance(value, list):
                for item in value:
                    add_option(name, item)
            else:
                cmd.append('--' + name)
                cmd.append(value)

        cmd = [self.mock_bin]

        if self.config_name:
            add_option('root', self.config_name)
        if self.config_dir:
            add_option('configdir', self.config_dir)

        for k, v in kwargs.items():
            add_option(k, v)

        cmd.append('--' + command)
        cmd.extend(args)
        return cmd
