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

import sys
import os
import tempfile
from commands import getstatusoutput
import logging

logger = logging.getLogger(__package__)


class MockDriver():
    def _init(self, release):
        self.releases = self.list_chroots()
        self.mock_bin = self.find_system_mock()
        self.srpm_templeate = '%s -r %s --resultdir %s --buildsrpm ' \
                              '--sources %s --spec %s'
        self.rpm_templeate = '%s -r %s --resultdir %s --rebuild %s'
        if release in self.releases:
            self.release = release
        else:
            sys.exit('There is no "%s" in mock chroot configs, '
                     'available: %s' % (release, self.releases))

    def list_chroots(self, path_to_configs='/etc/mock/'):
        """List all available chroot configurations

        :param path_to_configs: path to mock chroot config files
        :return: list of available chroots
        """

        if not os.path.exists(path_to_configs):
            sys.exit('There is no chroot configs path %' % path_to_configs)

        chroots = []
        for filename in self.files_with_extension(path_to_configs, '.cfg'):
            chroots.append(os.path.basename(os.path.splitext(filename)[0]))

        if not chroots:
            sys.exit('There is no chroot configs in %' % path_to_configs)

        return chroots

    @staticmethod
    def find_system_mock(mock_path='/usr/bin/mock'):
        """Trying to find system mockbuild binary

        :param mock_path: what searching, by default /usr/bin/mock
        :return: path to mock binary
        """

        rc, result = getstatusoutput('which %s' % mock_path)

        if rc != 0:
            sys.exit('Install mock using package manager')

        return result

    @staticmethod
    def path_exists(path):
        """Check path exists

        :param path: path to check
        :return bool
        """
        if os.path.exists(path):
            return True
        else:
            return False

    @staticmethod
    def find_spec_file(path):
        """Finding spec file in path

        :param path: path to search spec file
        :return absulute path of spec file
        """
        abspath = os.path.abspath(path)
        specs = []

        for filename in os.listdir(abspath):
            if filename.endswith(".spec"):
                specs.append(os.path.join(abspath, filename))

        if not specs:
            sys.exit('There is no spec files in %s' % abspath)

        return specs[0]

    def files_with_extension(self, path, extension):
        """Finding files in path with selected extension

        :param path: path to find files
        :param extension: extension pattern to find files
        :return: list of files
        """
        result = []

        if not self.path_exists(path):
            sys.exit("""%s doesn't exists""" % path)

        for filename in os.listdir(path):
            if filename.endswith(extension):
                result.append(os.path.join(path, filename))

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
        self._init(release)
        sources = os.path.abspath(sources)

        if not self.path_exists(sources):
            sys.exit('Sources exists "%s" ?' % sources)

        if not spec:
            spec = self.find_spec_file(sources)

        if not resultdir:
            resultdir = tempfile.mkdtemp(
                prefix='srpm_%s_' % os.path.split(sources)[1]
            )

        command = self.srpm_templeate % (
            self.mock_bin,
            self.release,
            resultdir,
            sources,
            spec
        )
        rc, stdout = getstatusoutput(command)

        srpms = self.files_with_extension(resultdir, '.src.rpm')

        return {
            'result': srpms,
            'rc': rc,
            'stdout': stdout.splitlines()
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
        self._init(release)
        validated_srpms = []
        result = {'rpms': []}
        # how else posible to validate srpm ?
        for srpm in srpms:
            if os.path.isfile(srpm):
                validated_srpms.append(os.path.abspath(srpm))

        if not resultdir:
            resultdir = tempfile.mkdtemp(prefix='rpm_')

        for srpm in validated_srpms:
            command = self.rpm_templeate % (
                self.mock_bin,
                self.release,
                resultdir,
                srpm
            )
            rc, stdout = getstatusoutput(command)

            result[os.path.basename(srpm)] = {
                'rc': rc,
                'stdout': stdout.splitlines(),
                'resultdir': resultdir
            }

        result['rpms'] = self.files_with_extension(resultdir, '.rpm')

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

    def build_package(self, release,  sources):
        """ Build package from sources

        :param release: release like 'centos-7-x86_64'
        :param sources: path to sources
        :return: list of builded packages
        """
        return self.build_rpm_from_sources(release, sources)
