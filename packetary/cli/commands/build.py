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
from packetary.cli.commands.utils import read_from_file


class BuildPackageCommand(BasePackagingCommand):
    """Builds the new package."""

    def get_parser(self, prog_name):
        parser = super(BuildPackageCommand, self).get_parser(prog_name)
        parser.add_argument(
            '-i',
            '--input-data',
            type=read_from_file,
            required=True,
            metavar='PATH',
            help='The list of sources to build packages,'
                 'the each source should contain path to source files and '
                 'path to spec file.'
        )

        parser.add_argument(
            '-o',
            '--output-dir',
            required=False,
            metavar='OUTPUT_DIR',
            default='.',
            help='The output directory, where will be saved packages, '
                 'which have been built.'
        )
        return parser

    def take_package_action(self, packaging_api, parsed_args):
        packages = packaging_api.build_packages(
            parsed_args.input_data, parsed_args.output_dir
        )
        self.stdout.write("Packages built:\n")
        for package in packages:
            self.stdout.write(package)
            self.stdout.write("\n")


def debug(argv=None):
    """Helper to debug the Build command."""
    from packetary.cli.app import debug
    debug("build", BuildPackageCommand, argv)


if __name__ == "__main__":
    debug()
