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
        group = parser.add_mutually_exclusive_group()
        parser.add_argument(
            '--repo-config',
            dest='repo_config',
            type=read_from_file,
            required=False,
            metavar='REPO_CONFIG',
            help="The path repo yaml file."
        )

        group.add_argument(
            '--packages-config',
            dest='packages_config',
            type=read_from_file,
            required=False,
            metavar='PACKAGES_CONFIG',
            help='Many packages to build,'
                 ' is specified in yaml file with keys: src, spec.'
        )

        parser.add_argument(
            '-r',
            '--release',
            dest='release',
            type=str,
            required=False,
            metavar='RELEASE',
            default='centos-7-x86_64',
            help='The target distributive name, version and architecture.'
        )

        group.add_argument(
            '-s',
            '--sources-dir',
            dest='sources_dir',
            type=str,
            required=False,
            metavar='SOURCES_DIR',
            default='.',
            help='The sources directory for build.'
        )

        parser.add_argument(
            '-o',
            '--output-dir',
            dest='output_dir',
            type=str,
            required=False,
            metavar='OUTPUT_DIR',
            default='.',
            help='The output directory for build.'
        )

        parser.add_argument(
            '--spec-file',
            dest='spec_file',
            type=str,
            required=False,
            metavar='SPEC_FILE',
            default=None,
            help='Spec file for package.'
        )

        return parser

    def take_package_action(self, api, parsed_args):

        if parsed_args.repo_config:
            repos = parsed_args.repo_config.get(parsed_args.type, None)
            if not repos:
                raise ValueError(
                    'Failed to get section {0} from repo config.'
                    'Available are {1}'.format(
                        parsed_args.type,
                        parsed_args.repo_config.keys()
                        )
                    )
        else:
            repos = None

        if parsed_args.packages_config:
            result = []
            for package_item in parsed_args.packages_config:
                packages = api.build_packages(
                    package_item.get('release', None),
                    package_item.get('src', package_item.get('source', './')),
                    package_item.get('spec', None),
                    parsed_args.output_dir,
                    repos
                )
                result.append((
                    package_item.get('src', package_item.get('source', './')),
                    packages
                ))

            self.stdout.write("Successfully build:")
            for result_item in result:
                self.stdout.write(
                    "\n => {0}\n{1}".format(
                        result_item[0],
                        '\n'.join(result_item[1])
                    )
                )
        else:
            packages = api.build_packages(
                parsed_args.release,
                parsed_args.sources_dir,
                parsed_args.spec_file,
                parsed_args.output_dir,
                repos
            )
            self.stdout.write(
                "Successfully build:\n{0}".format('\n'.join(packages))
            )


def debug(argv=None):
    """Helper to debug the Build command."""
    from packetary.cli.app import debug
    debug("build", BuildPackageCommand, argv)


if __name__ == "__main__":
    debug()
