#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''`betse`-specific script writer for `setuptools`.'''

# ....................{ IMPORTS                            }....................
from pkg_resources import Distribution
from setup import util
from setuptools.command import easy_install
from setuptools.command.easy_install import ScriptWriter

# ....................{ CONSTANTS                          }....................
SCRIPT_TEMPLATE = """
# Auto-generated by BETSE's "build_scripts" setuptools command.

# If this script is called directly rather than imported, run BETSE; else, do
# nothing. Since this script should never be imported, BETSE should always be
# run. Your mileage may vary.
if __name__ == '__main__':
    import sys
    from {entry_point_module} import {entry_point_func}

    # Propagate the return value of such function (hopefully a single-
    # byte integer) to the calling shell as this script's exit status.
    sys.exit({entry_point_func}())
"""
'''
Script template to be formatted by `ScriptWriterSimple.get_script_args()`.
'''

# ....................{ COMMANDS                           }....................
def add_setup_commands(setup_options: dict) -> None:
    '''
    Add wrapper script-specific commands to the passed dictionary of
    `setuptools` options.
    '''
    assert isinstance(setup_options, dict),\
        '"{}" not a dictionary.'.format(setup_options)

    # Replace the default "setuptools" class for writing scripts with ours.
    easy_install.get_script_args = ScriptWriterSimple.get_script_args

# ....................{ WRITER                             }....................
class ScriptWriterSimple(ScriptWriter):
    '''
    Write Python script wrappers suitable for use with system-wide installations
    of Python packages (e.g., via the `betse`-specific `symlink` command).

    The default `ScriptWriter` class provided by `setuptools` writes Python
    script wrappers attempting to import the `pkg_resources` for the
    corresponding Python package. Since no `pkg_resources` are installed for
    system-wide installations, such scripts *always* fail, implying such scripts
    to be suitable *only* for use with user-specific venvs.

    This class corrects such deficiency, albeit at a minor cost of ignoring the
    `pkg_resources` for Python packages installed in the customary way.
    '''

    @classmethod
    def get_script_args(
        cls,
        distribution: Distribution,
        executable = easy_install.sys_executable,
        wininst = False):
        '''
        Yield write_script() argument tuples for a distribution's entry points.
        '''
        # Class with which to write such scripts.
        gen_class = cls.get_writer(wininst)

        # Shebang line prefixing the contents of all such scripts.
        script_shebang = easy_install.get_script_header("", executable, wininst)

        # For each such script...
        for script_basename, script_type, entry_point in\
            util.package_distribution_entry_points(distribution):
            # Script contents, formatted according to such template.
            script_text = SCRIPT_TEMPLATE.format(
                entry_point_module = entry_point.module_name,
                entry_point_func = entry_point.attrs[0],
            )

            # Yield a tuple containing such metadata to the caller.
            for res in gen_class._get_script_args(
                script_type, script_basename, script_shebang, script_text):
                yield res

# --------------------( WASTELANDS                         )--------------------
        # # For each type of script...
        # for type_ in 'console', 'gui':
        #     script_group = type_ + '_scripts'
        #
        #     # For the basename and entry point of each script of such type...
        #     for script_basename, entry_point in\
        #         dist.get_entry_map(script_group).items():

                # Entry point module and function split from such entry point
                # (e.g., "betse.cli.cli:main").
                # entry_point_module, entry_point_func = entry_point.split(':')
                    # entry_point_module = entry_point_module,
                    # entry_point_func = entry_point_func,

# Since setuptools provides installation- but *NOT* build-specific commands,
# defer to the latter provided by distutils.
# from distutils.command.build_scripts import build_scripts
# from setup import error
# import os, sys

    # See "symlink.py" for commentary.
    # setup_options['cmdclass']['build_scripts'] = betse_build_scripts
    # betse_build_scripts._setup_options = setup_options

# ....................{ CLASSES ~ build                    }....................
# class betse_build_scripts(build_scripts):
#     '''
#     Create all Python script wrappers for `betse` in a manner compatible with
#     system-wide installation.
#
#     Unlike scripts created by the default `build_scripts` command, scripts
#     created by this class do _not_ attempt to import `setuptools`-specific
#     package resources and hence are compliant with editable installations.
#     '''
#
#     def run(self):
#         '''Run the current command and all subcommands thereof.'''
#         # If the current operating system is *NOT* POSIX-compatible, such system
#         # does *NOT* support conventional shebang-driven shell scripts. Raise an
#         # exception.
#         error.die_if_os_non_posix()
#
#         # Template for the contents of such scripts.
#         script_template = """#!{python_interpreter_filename}
#         # Auto-generated by BETSE's "build_scripts" setuptools command.
#
#         # If this script is called directly rather than imported (...which it
#         # should *NEVER* be), run BETSE.
#         if __name__ == '__main__':
#             import sys
#             from {entry_point_module} import {entry_point_func}
#
#             # Propagate the return value of such function (hopefully a single-
#             # byte integer) to the calling shell as this script's exit status.
#             sys.exit({entry_point_func}())
#         """
#
#         # Absolute path of all scripts created by this method.
#         script_filenames = []
#
#         # Make the temporary build directory to which such scripts will be
#         # subsequently written.
#         self.mkpath(self.build_dir)
#
#         # Make the script specified by each entry point specification (e.g.,
#         # "'betse = betse.cli.cli:main'").
#         for entry_point_specs in self._setup_options['entry_points'].values():
#             for entry_point_spec in entry_point_specs:
#                 # Basename (e.g., "betse") and entry point (e.g.,
#                 # "betse.cli.cli:main") of such script split from such
#                 # specification on "=", stripping all leading and trailing
#                 # whitespace from such substrings after doing so.
#                 script_basename, entry_point = entry_point_spec.split('=')
#                 script_basename = script_basename.strip()
#                 entry_point = entry_point.strip()
#
#                 # Absolute path of such script.
#                 script_filename = os.path.join(self.build_dir, script_basename)
#
#                 # Add such path to the list of such paths.
#                 script_filenames.append(script_filename)
#
#                 # Entry point module and function split from such entry point.
#                 entry_point_module, entry_point_func = entry_point.split(':')
#
#                 # Write such script.
#                 with open(script_filename, 'w') as script_file:
#                     print('Building script "{}".'.format(script_filename))
#                     script_file.write(script_template.format(
#                         python_interpreter_filename = sys.executable,
#                         entry_point_module = entry_point_module,
#                         entry_point_func = entry_point_func,
#                     ))
#
#         # setuptools expects this method to return such list. Satisfy its
#         # shameless desires.
#         return script_filenames

# from distutils.errors import DistutilsPlatformError
        # if os.name == 'nt':
        #     raise DistutilsPlatformError(
        #         'Current command