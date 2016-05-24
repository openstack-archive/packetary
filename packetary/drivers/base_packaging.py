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

import abc
import logging
import six


@six.add_metaclass(abc.ABCMeta)
class PackagingDriverBase(object):
    """The super class for Packaging Drivers.

    For implementing support of new type of packaging:
    - inherit this class
    - implement all abstract methods
    - register implementation in 'packetary.drivers' namespace
    """

    def __init__(self):
        self.logger = logging.getLogger(__package__)

    @abc.abstractmethod
    def build_packages(self, release, sources, spec_file, output_dir, repos):
        """Build package from sources.

        :param release: release like 'centos-7-x86_64'
        :type release: str

        :param sources: path to sources
        :type sources: str

        :param spec_file: path to spec file ( if necessary )
        :type spec_file: str or None

        :param output_dir: directory for new packages
        :type output_dir: str

        :param repos: list of build chroot repositories
        :type repos: list

        :return: list of builded packages
        :rtype: list[str]
        """
