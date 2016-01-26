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

import pbr.version

from packetary.api import Configuration
from packetary.api import Context
from packetary.api import RepositoryApi


__all__ = [
    "Configuration",
    "Context",
    "RepositoryApi",
]

try:
    __version__ = pbr.version.VersionInfo(
        'packetary').version_string()
except Exception as e:
    # when run tests without installing package
    # pbr may raise exception.
    print("ERROR:", e)
    __version__ = "0.0.0"
