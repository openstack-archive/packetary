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

from packetary.cli.commands.base import BasePackagingCommand


class BuildPackageCommand(BasePackagingCommand):
    """Builds the new package."""

    def get_parser(self, prog_name):
        parser = super(BuildPackageCommand, self).get_parser(prog_name)

        parser.add_argument(
            '-r',
            '--release',
            type=str,
            required=False,
            metavar='RELEASE',
            default='centos-7-x86_64',
            help='The target distributive name, version and architecture.'
        )

        parser.add_argument(
            '-s',
            '--sources-dir',
            type=str,
            required=False,
            metavar='SOURCES_DIR',
            default='.',
            help='The sources directory for build.'
        )

        return parser

    def take_package_action(self, api, parsed_args):
        packages = api.build_packages(
            parsed_args.release,
            parsed_args.sources_dir
        )
        self.stdout.write(
            "Successfully build:\n{0}".format(
                    '\n'.join(packages)
            )
        )


def debug(argv=None):
    """Helper to debug the Build command."""
    from packetary.cli.app import debug
    debug("build", BuildPackageCommand, argv)


if __name__ == "__main__":
    debug()
