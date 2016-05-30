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
        pos1 = text.find(':')
        if pos1 != -1:
            epoch = text[0:pos1]
        else:
            epoch = 0
        pos1 += 1
        pos2 = text.find('-', pos1)
        if pos2 != -1:
            version = text[pos1: pos2]
            release = text[pos2 + 1:]
        else:
            version = text[pos1:]
            release = None
        return cls(epoch, version, release)

    def cmp(self, other):
        if not isinstance(other, PackageVersion):
            other = PackageVersion.from_string(str(other))

        if not isinstance(other, PackageVersion):
            raise TypeError
        if self.epoch < other.epoch:
            return -1
        if self.epoch > other.epoch:
            return 1

        res = self._cmp_version_part(self.version, other.version)
        if res != 0:
            return res
        if self.release and other.release:
            return self._cmp_version_part(self.release, other.release)
        return 0

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

    @classmethod
    def _order(cls, x):
        """Return an integer value for character x"""
        if x.isdigit():
            return int(x) + 1
        if x.isalpha():
            return ord(x)
        return ord(x) + 256

    @classmethod
    def _cmp_version_string(cls, version1, version2):
        """Compares two versions as string."""
        la = [cls._order(x) for x in version1]
        lb = [cls._order(x) for x in version2]
        while la or lb:
            a = 0
            b = 0
            if la:
                a = la.pop(0)
            if lb:
                b = lb.pop(0)
            # handle the tilde separator, which is ~ = (int) 382
            # _order("~") == 382
            # if both versions have tilde then let's continue
            if a == b == 382:
                continue
            if a == 382:
                return -1
            if b == 382:
                return 1
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0

    @classmethod
    def _cmp_version_part(cls, version1, version2):
        """Compares two versions."""
        ver1_it = iter(version1)
        ver2_it = iter(version2)
        while True:
            v1 = next(ver1_it, None)
            v2 = next(ver2_it, None)

            if v1 is None or v2 is None:
                if v1 is not None:
                    return 1
                if v2 is not None:
                    return -1
                return 0

            if v1.isdigit() and v2.isdigit():
                a = int(v1)
                b = int(v2)
                if a < b:
                    return -1
                if a > b:
                    return 1
            else:
                r = cls._cmp_version_string(v1, v2)
                if r != 0:
                    return r
