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

    def get_data_schema(self):
        return RPM_PACKAGING_SCHEMA

    def get_for_caching(self, data):
        return [data['src'], data['rpm']['spec']]

    def build_packages(self, data, cache, output_dir, consumer):
        src = cache[data['src']]
        spec = cache[data['rpm']['spec']]
        options = data['rpm'].get('options', {})

        with utils.create_tmp_dir() as tmpdir:
            self._buildsrpm(
                resultdir=tmpdir, spec=spec, sources=src, **options
            )
            srpms_dir = os.path.join(output_dir, 'SRPM')
            utils.ensure_dir_exist(srpms_dir)
            srpms = glob.iglob(os.path.join(srpms_dir, '*.src.rpm'))
            rpms_dir = os.path.join(output_dir, 'RPM')
            utils.ensure_dir_exist(rpms_dir)
            self._rebuild(srpms, resultdir=tmpdir, **options)

            # rebuild commands rebuilds source rpm too
            # notify only about last version
            for rpm in utils.move_files(tmpdir, srpms_dir, '*.src.rpm'):
                consumer(rpm)

            for rpm in utils.move_files(tmpdir, rpms_dir, '*.rpm'):
                consumer(rpm)

    def _buildsrpm(self, spec, sources, **kwargs):
        """Builds the specified SRPM either from a spec file.

        :param spec: Specifies spec file to use to build an SRPM
        :param sources: Specifies sources (either a single file or a directory
                        of files)to use to build an SRPM
        :kwargs: the other mock parameters, for details see `man mock`
        """
        self.logger.info("buildsrpm '%s' '%s'", spec, sources)
        return self._invoke_mock(
            'buildsrpm', spec=spec, sources=sources, **kwargs
        )

    def _rebuild(self, srpms, **kwargs):
        """Rebuilds the specified SRPM(s).

        :param srpms: The list of SRPM(s) for rebuilding.
        :kwargs: the other mock parameters, for details see `man mock`
        """
        self.logger.info("rebuild %s", srpms)
        return self._invoke_mock('rebuild', *srpms, **kwargs)

    def _invoke_mock(self, command, *args, **kwargs):
        cmdline = self._assemble_cmdline(command, args, kwargs)
        self.logger.debug("start command: '%'", ' '.join(cmdline))
        subprocess.check_call(cmdline)

    def _assemble_cmdline(self, command, args, kwargs):
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
