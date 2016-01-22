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


class Repository(object):
    """Structure to describe repository object."""

    def __init__(self, name, url, architecture, origin=None,
                 path=None, section=None):
        """Initialises.

        :param name: the repository`s name, may be tuple of strings
        :param url: the repository`s URL
        :param architecture: the repository`s architecture
        :param origin: optional, the repository`s origin
        :param path: the repository relative path, used for mirroring
        :param section: the repository section
        """
        self.architecture = architecture
        self.name = name
        self.origin = origin or ""
        self.url = url
        self.section = section
        self.path = path

    def __str__(self):
        if not self.section:
            return self.url

        if isinstance(self.section, tuple):
            section_str = " ".join(self.section)
        else:
            section_str = self.section
        return " ".join((self.url, section_str))

    def __copy__(self):
        """Creates shallow copy of package."""
        return Repository(**self.__dict__)

    def __hash__(self):
        return hash((self.url, self.section))
