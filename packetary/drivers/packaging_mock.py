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

import glob
import logging
import os
import shlex
import subprocess
import tempfile

from distutils.spawn import find_executable
from packetary.drivers.base_packaging import PackagingDriverBase


logger = logging.getLogger(__package__)


class MockDriver(PackagingDriverBase):
    def __init__(self):
        self.releases = self.get_chroots()
        self.mock_bin = self.find_system_mock()
        self.srpm_template = '{0} -r {1} --resultdir {2} --buildsrpm ' \
                             '--sources {3} --spec {4}'
        self.rpm_template = '{0} -r {1} --resultdir {2} --rebuild {3}'

    def check_release(self, release):
        """Validate release

        :param release: os release, like 'centos-7-x86_64'
        """
        if release not in self.releases:
            raise ValueError(
                'There is no "{0}" in mock chroot configs, '
                'available: {1}'.format(release, self.releases)
            )

    @staticmethod
    def get_chroots(path_to_configs='/etc/mock/'):
        """List all available chroot configurations

        :param path_to_configs: path to mock chroot config files
        :return: list of available chroots
        """

        if not os.path.exists(path_to_configs):
            raise ValueError(
                'There is no chroot configs path {0}'.format(path_to_configs)
            )

        chroots = []
        for filename in glob.glob(os.path.join(path_to_configs, '*.cfg')):
            chroots.append(os.path.basename(os.path.splitext(filename)[0]))

        return chroots

    @staticmethod
    def sys_execute(command=None):
        """Execute system command

        :param command: command to run
        :return: stdout of executed command
        """
        if not command:
            raise ValueError(
                'Please specify command to execute'
            )

        _command = shlex.split(command)

        return subprocess.check_output(_command)

    @staticmethod
    def find_system_mock(mock_path='/usr/bin/mock'):
        """Trying to find system mockbuild binary

        :param mock_path: what searching, by default /usr/bin/mock
        :return: path to mock binary
        """
        result = find_executable(mock_path)

        if not result:
            raise ValueError('Install mock using package manager')

        return result

    def build_srpm(self, release, sources, spec=None, resultdir=None):
        """Build SRPM from sources and spec file

        :param release: release like 'centos-7-x86_64'
        :param sources: path to sources
        :param spec: path to spec file,
                if it not in sources dir
        :param resultdir: path to put srpm
        :return: dict with keys:
                    result: list of srpms
                    rc: mock return code
                    stdout: list of mock stdout
        """
        self.check_release(release)
        sources = os.path.abspath(sources)

        if not os.path.exists(sources):
            raise ValueError('Sources exists "{0}" ?'.format(sources))

        if not spec:
            available_specs = glob.glob(os.path.join(sources, '*.spec'))

            if not available_specs:
                raise ValueError(
                    'There is no spec file in sources, please specify it'
                )
            else:
                spec = available_specs[0]

        if not resultdir:
            resultdir = tempfile.mkdtemp(
                prefix='srpm_{0}_'.format(os.path.split(sources)[1])
            )

        elif not os.path.isdir(resultdir):
            raise ValueError(
                'Result dir "{0}" not exists'.format(resultdir)
            )

        command = self.srpm_template.format(
            self.mock_bin,
            release,
            resultdir,
            sources,
            spec
        )

        stdout = self.sys_execute(command)
        srpms = glob.glob(os.path.join(resultdir, '*.src.rpm'))

        return {
            'result': srpms,
            'stdout': stdout
        }

    def build_rpm(self, release, srpms, resultdir=None):
        """Build RPM from SRPM

        :param release: release like 'centos-7-x86_64'
        :param srpms: list of srpms to rebuild
        :param resultdir: path to put rpm
        :return: dict with keys:
                    srpm name:
                        rpms: list of builded rpms
                        resultdir: path to rpm dir
                        rc: mock return code
                        stdout: list of mock stdout
        """
        self.check_release(release)
        validated_srpms = []
        result = {'rpms': []}

        for srpm in srpms:
            if os.path.isfile(srpm):
                validated_srpms.append(os.path.abspath(srpm))

        if not validated_srpms and srpms:
            raise ValueError('There is no valid srpms')

        if not resultdir:
            resultdir = tempfile.mkdtemp(prefix='rpm_')
        elif not os.path.isdir(resultdir):
            raise ValueError(
                'Result dir "{0}" not exists'.format(resultdir)
            )

        for srpm in validated_srpms:
            command = self.rpm_template.format(
                self.mock_bin,
                release,
                resultdir,
                srpm
            )
            stdout = self.sys_execute(command)

            result[os.path.basename(srpm)] = {
                'stdout': stdout,
                'resultdir': resultdir
            }

        result['rpms'] = glob.glob(os.path.join(resultdir, '*.rpm'))

        return result

    def build_rpm_from_sources(self,
                               release,
                               sources,
                               spec=None,
                               resultdir=None):
        """Build RPM from sources and spec file

        :param release: release like 'centos-7-x86_64'
        :param sources: path to sources
        :param spec: path to spec file,
                if it not in sources dir
        :param resultdir: path to put srpm and rpms
        :return: dict with srpm and rpm building
        """
        srpms = self.build_srpm(release, sources, spec, resultdir)
        rpm = self.build_rpm(release, srpms['result'])
        return rpm['rpms']

    def build_packages(self, release, sources, spec_file=None):
        """Build package from sources

        :param release: release like 'centos-7-x86_64'
        :param sources: path to sources
        :param spec_file: path to spec file
        :return: list of builded packages
        """
        return self.build_rpm_from_sources(release, sources, spec_file)
