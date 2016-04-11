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

from distutils.spawn import find_executable
from packetary.drivers.base_packaging import PackagingDriverBase


logger = logging.getLogger(__package__)


class SbuildDriver(PackagingDriverBase):
    def __init__(self):
        self.sbuild_bin = self.find_system_sbuild()
        self.chroot_components = "main,universe,multiverse,restricted"
        self.mirror = "http://mirror.fuel-infra.org/pkgs/ubuntu/"
        self.create_chroot_template = "sbuild-createchroot --components=" \
                                      "{0} {1} `mktemp -d` {2}"
        self.chroot_parameters = self.get_chroots()
        self.releases = set()
        for chroot in self.chroot_parameters:
            if chroot.get('Name', None):
                self.releases.add(chroot['Name'])

    @staticmethod
    def get_chroots_deprecated(list_command='schroot -l'):
        """List all available chroot configurations

        :param list_command: system command to list avaliable chroots
        :return: list of tuples with type and name of chroots
        """
        chroots = []

        stdout = SbuildDriver.sys_execute(list_command)
        for line in stdout.splitlines():
            chroots.append(tuple(line.split(':')))

        return chroots

    @staticmethod
    def get_chroots(list_verbose='schroot -i'):
        """List all available chroot configurations

        :param list_verbose: system command to list
                             avaliable chroots with parameters
        :return: list of dicts with chroots parameters
        """
        chroots = []
        stdout = SbuildDriver.sys_execute(list_verbose)

        curr_chroot = {}
        lines_count = len(stdout.splitlines())
        for n, i in enumerate(stdout.splitlines()):
            line = [x for x in i.split('  ') if x]

            # check parameter not empty
            if len(line) == 2 and line[1].lstrip():
                curr_chroot.update(
                    {line[0].rstrip(): line[1].lstrip()}
                )

            # end of chroot config section
            if not line or n + 1 == lines_count:
                chroots.append(curr_chroot)
                curr_chroot = {}

        return chroots

    def create_chroot(self, dist='trusty', mirror=None):
        """Create build chroot

        :param dist: chroot distributive
        :param mirror: mirror of distributive
        :return stdout of creating chroot
        """
        if mirror:
            _mirror = mirror
        else:
            _mirror = self.mirror

        create_chroot_command = self.create_chroot_template.format(
            self.chroot_components,
            dist,
            _mirror
        )

        try:
            return self.sys_execute(create_chroot_command)
        except Exception:
            raise ValueError(
                'Failed to create chroot {0}. {1}'.format(
                    dist,
                    Exception
                )
            )

    def add_apt_sources(self, chroot_name, mirror):
        for chroot in self.chroot_parameters:
            if chroot.get('Name', None) == chroot_name and \
               chroot.get('Type', None) == 'directory':
                _chroot = chroot
            else:
                raise ValueError("Can't update {0} chroot".format(chroot_name))

        chroot_path = _chroot.get('Directory', None)
        apt_sources_d = os.path.join(chroot_path, 'etc/apt/sources.list.d/')
        apt_sources_file = '{0}.list'.format('_'.join(mirror.split('/')[2:-1]))
        if not os.path.isdir(apt_sources_d):
            raise ValueError('There is no apt sources.list.d in {0}'.format(
                apt_sources_d
            ))

        try:
            with open(
                    os.path.join(
                        apt_sources_d,
                        apt_sources_file
                    ), 'w') as sources_file:

                sources_file.write(
                    'deb {0} {1} {2}'.format(
                        mirror,
                        chroot.get('Name', 'unknown-').split('-')[0],
                        self.chroot_components
                    )
                )

                sources_file.write(
                    'deb {0} {1}-update {2}'.format(
                        mirror,
                        chroot.get('Name', 'unknown-').split('-')[0],
                        self.chroot_components
                    )
                )
        except Exception:
            raise ValueError(
                'Failed to write apt sources.d file {0}. {1}'.format(
                    os.path.join(apt_sources_d, apt_sources_file),
                    Exception
                )
            )

        self.sys_execute(
            'sbuild-update -udcar {0}'.format(
                chroot_name.split('-')[0]
            )
        )

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
    def find_system_sbuild(sbuild_path='/usr/bin/sbuild'):
        """Trying to find system sbuild binary

        :param sbuild_path: what searching, by default /usr/bin/sbuild
        :return: path to sbuild binary
        """
        result = find_executable(sbuild_path)

        if not result:
            raise ValueError('Install sbuild using package manager')

        return result

    def build_deb_from_sources(self, release, sources):
        """Build package from sources

        :param release: release like 'trusty-amd64-sbuild'
        :param sources: path to sources
        :return: list of builded packages
        """
        dist = release.split('-')[0]
        if release not in self.releases:
            self.create_chroot(dist)
            self.add_apt_sources(release, self.mirror)

        os.chdir(sources)
        self.sys_execute('sudo sbuild -d {1} -c {2}'.format(
            os.path.abspath(sources),
            dist,
            release
        ))

        path_to_packages = os.path.join(sources, '../')
        return glob.glob(os.path.join(path_to_packages, '*.deb'))

    def build_packages(self, release, sources, spec_file):
        """Driver interface for packetary

        :param release: release like 'trusty-amd64-sbuild'
        :param sources: path to sources
        :parama spec_file: legacy of mock driver,
                           need to rewrite
        :return: list of builded packages
        """
        if 'x86_64' in release:
            release.replace('x86_64', 'amd64')

        return self.build_deb_from_sources(
            release,
            sources
        )
