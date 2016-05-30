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

from packetary.objects.base import ComparableObject
from rpmUtils.miscutils import stringToVersion
from rpmUtils.miscutils import compareEVR


class PackageVersion(ComparableObject):
    """The Package version."""

    __slots__ = ["epoch", "version", "release"]

    def __init__(self, epoch, version, release=None):
        self.epoch = int(epoch or 0)
        self.version = tuple(version.split('.'))
        if release:
            self.release = tuple(release.split('.'))
        else:
            self.release = None

    @classmethod
    def from_string(cls, text):
        """Constructs from string.

        :param text: the version in format '[{epoch-}]-{version}-{release}'
        """
        (epoch, version, release) = stringToVersion(text)
        return cls(epoch, version, release)

    def cmp(self, other):
        if not isinstance(other, PackageVersion):
            other = PackageVersion.from_string(str(other))

        if not isinstance(other, PackageVersion):
            raise TypeError
        # if self.epoch < other.epoch:
        #     return -1
        # if self.epoch > other.epoch:
        #     return 1

        # res = self._cmp_version_part(self.version, other.version)
        # if res != 0:
        #     return res
        # if self.release and other.release:
        #     return self._cmp_version_part(self.release, other.release)
        # return 0
        return compareEVR((self.epoch, self.version, self.release),
                          (other.epoch, other.version, other.release))

    def __eq__(self, other):
        if other is self:
            return True
        return self.cmp(other) == 0

    def __str__(self):
        if self.release:
            return "{0}:{1}-{2}".format(
                self.epoch,
                ".".join(str(x) for x in self.version),
                ".".join(str(x) for x in self.release)
            )
        else:
            return "{0}:{1}".format(
                self.epoch,
                ".".join(str(x) for x in self.version),
            )
