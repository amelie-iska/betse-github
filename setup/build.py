#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
`betse`-specific monkey patching of `setuptools`'s `ScriptWriter` class.

Such patching renders such class for use with editable installations of Python
packages (e.g., via `betse`'s `symlink` command). The default `ScriptWriter`
implementation writes scripts attempting to import the `setuptools`-installed
package resources for such packages. Since no such resources are installed for
editable installations, such scripts *always* fail and hence are suitable *only*
for use with user-specific venvs.

Such patching corrects this deficiency, albeit at a minor cost of ignoring the
package resources provided by Python packages installed in the customary way.
While there exist alternatives, this appears to be the most robust means of
maintaining backward compatibility with older `setuptools` versions.
'''

# ....................{ IMPORTS                            }....................
from pkg_resources import Distribution
from setup import util
from setuptools.command.easy_install import ScriptWriter, WindowsScriptWriter

# ....................{ CONSTANTS                          }....................
SCRIPT_TEMPLATE = '''
# Auto-generated by the "build_scripts" setuptools command.
import importlib, sys

def is_module_root(module_name: str) -> bool:
    """
    `True` if the **top-level module** (i.e., module whose name contains no `.`
    characters) with the passed fully-qualified name is importable under the
    active Python interpreter.

    If this module is _not_ importable via the standard
    `importlib.find_loader()` mechanism (e.g., the OS X-specific `PyObjCTools`
    package), this module may also be imported as an additional side effect.
    """
    assert isinstance(module_name, str),\\
        '"{{}}" not a string.'.format(module_name)

    # If this is *NOT* a top-level module, raise an exception.
    if '.' in module_name:
        raise ImportError('Module "{{}}" not a top-level module.'.format(
            module_name))

    # See betse.util.python.modules.is_module() for implementation details.
    try:
        return importlib.find_loader(module_name) is not None
    except ValueError:
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

# If this script is imported by another module rather than run directly,
# noop by printing a non-fatal warning and then returning. While this script
# should *NEVER* be imported, contemptible edge cases do happen.
# Else, this script is run directly. Let's do this.
if __name__ == '__main__':
    # If the root parent package of this entry module is unimportable, raise a
    # human-readable exception. For inscrutable reasons, testing for whether
    # this entry module itself is importable is highly non-trivial under Python
    # 3.3 but *NOT* Python >= 3.4. While requiring Python >= 3.4 above would
    # obviate this, such version requirements are best asserted in the main
    # application codebase. Instead, we defer to the next best test.
    if not is_module_root('{entry_package_root}'):
        raise ImportError(
            'Package "{entry_package_root}" unimportable. Consider running either:\\n'
            '\\tsudo python3 setup.py install\\n'
            '\\tsudo python3 setup.py symlink')

    # Import the entry module.
    import {entry_module} as entry_module

    # For debugging purposes, print the absolute path of this module.
    #print('{entry_module}: ' + entry_module.__file__)
    {entry_func_code}
# If this script is imported by another module rather than run directly,
# noop by printing a non-fatal warning and then returning. While this script
# should *NEVER* be imported, contemptible edge cases do happen.
# Else, this script is run directly. Let's do this.
else:
    print('WARNING: Entry point imported rather than run.', file=sys.stderr)
'''
'''
Script template to be formatted by `ScriptWriterSimple.get_script_args()`.
'''

SCRIPT_ENTRY_FUNC_SUBTEMPLATE = '''
    # If this module requires an entry function to be run, call such function.
    # For POSIX compliance, the value returned by this function (ideally a
    # single-byte integer) will be propagated back to the calling shell as this
    # script's exit status.
    sys.exit(entry_module.{entry_func}())
'''
'''
Script subtemplate to be formatted by `ScriptWriterSimple.get_script_args()`
for entry points requiring an entry function to be called.

This excludes entry points for which merely importing the desired entry module
suffices to implicitly run that entry point -- typically, entry modules with
basename `__main__`.
'''

# ....................{ COMMANDS                           }....................
def add_setup_commands(metadata: dict, setup_options: dict) -> None:
    '''
    Add commands building distribution entry points to the passed dictionary of
    `setuptools` options.
    '''
    assert isinstance(setup_options, dict),\
        '"{}" not a dictionary.'.format(setup_options)

    # If the ScriptWriter.get_args() method exists, this is a recent version of
    # setuptools. In such case, monkey-patch such method.
    if hasattr(ScriptWriter, 'get_args'):
        ScriptWriter.get_args = _get_args
    # Else, this is an older version of setuptools. In such case, monkey-patch
    # the deprecated ScriptWriter.get_script_args() method.
    else:
        ScriptWriter.get_script_args = _get_script_args

# ....................{ PATCHES                            }....................
# Functions monkey-patching existing methods of the "ScriptWriter" class above
# and hence defined to have the same method signatures. The "cls" parameter
# implicitly passed to such methods by the @classmethod decorator is guaranteed
# to be the "ScriptWriter" class.

@classmethod
def _get_args(
    cls: type,
    distribution: Distribution,
    script_shebang: str = None
):
    '''
    Yield `write_script()` argument tuples for the passed distribution's **entry
    points** (i.e., platform-specific executables running such distribution).

    This function monkey-patches the `ScriptWriter.get_args()` class function.
    '''
    # Default such shebang line if unpassed.
    if script_shebang is None:
        script_shebang = cls.get_header()

    assert isinstance(cls, type), '"{}" not a class.'.format(cls)
    assert isinstance(script_shebang, str),\
        '"{}" not a string.'.format(script_shebang)

    # For each entry point...
    for script_basename, script_type, entry_point in\
        util.package_distribution_entry_points(distribution):
        # Script code calling the main function in this entry module to be
        # called if any or the empty string otherwise.
        if len(entry_point.attrs):
            script_entry_func_code = SCRIPT_ENTRY_FUNC_SUBTEMPLATE.format(
                entry_func = entry_point.attrs[0])
        else:
            script_entry_func_code = ''

            # Print a non-fatal warning, as the resulting script may *NOT*
            # necessarily be runnable or freezable as expected.
            util.output_warning(
                'Entry module "{}" entry function undefined.'.format(
                entry_point.module_name))

        # Script contents, formatted according to such template.
        script_code = SCRIPT_TEMPLATE.format(
            entry_func_code = script_entry_func_code,

            # Fully-qualified name of this entry module's root parent package.
            entry_package_root = entry_point.module_name.split('.')[0],

            # Fully-qualified name of this entry module.
            entry_module = entry_point.module_name,
        )

        # Yield a tuple containing such metadata to the caller.
        for script_tuple in cls._get_script_args(
            script_type, script_basename, script_shebang, script_code):
            yield script_tuple

@classmethod
def _get_script_args(
    cls: type,
    distribution: Distribution,
    executable = None,
    is_windows_vanilla: bool = False
):
    '''
    Yield `write_script()` argument tuples for the passed distribution's **entry
    points** (i.e., platform-specific executables running such distribution).

    This function monkey-patches the deprecated
    `ScriptWriter.get_script_args()` class function.
    '''
    assert isinstance(cls, type), '"{}" not a class.'.format(cls)

    # Platform-specific entry point writer.
    script_writer = (
        WindowsScriptWriter if is_windows_vanilla else ScriptWriter).best()

    # Shebang line prefixing the contents of all such scripts.
    script_shebang = cls.get_script_header(
        '', executable, is_windows_vanilla)

    # Defer to the newer _get_args() function.
    return script_writer.get_args(distribution, script_shebang)

# --------------------( WASTELANDS                         )--------------------
            # Name of the main function in this entry module to be called if
            # any or the empty string otherwise.
            # entry_func = script_entry_func_text\
            #     entry_point.attrs[0] if len(entry_point.attrs) else '',
# SCRIPT_TEMPLATE = """
# # Auto-generated by BETSE's "build_scripts" setuptools command.
#
# # If this script is called directly rather than imported, run BETSE; else, do
# # nothing. Since this script should never be imported, BETSE should always be
# # run. Your mileage may vary.
# if __name__ == '__main__':
#     import sys
#     from {entry_point_module} import {entry_point_func}
#
#     # Propagate the return value of such function (hopefully a single-
#     # byte integer) to the calling shell as this script's exit status.
#     sys.exit({entry_point_func}())
# """

    # If a shebang line was passed (e.g., if the current platform is *NOT*
    # Windows), validate such line.
# from setuptools.command import easy_install
    # # Class with which to write such scripts.
    # gen_class = cls.get_writer(is_windows_vanilla)

    # # Shebang line prefixing the contents of all such scripts.
    # script_shebang = easy_install.get_script_header(
    #     '', executable, is_windows_vanilla)

    # # For each such script...
    # for script_basename, script_type, entry_point in\
    #     util.package_distribution_entry_points(distribution):
    #     # Script contents, formatted according to such template.
    #     script_text = SCRIPT_TEMPLATE.format(
    #         entry_point_module = entry_point.module_name,
    #         entry_point_func = entry_point.attrs[0],
    #     )
    #
    #     # Yield a tuple containing such metadata to the caller.
    #     for res in gen_class._get_script_args(
    #         script_type, script_basename, script_shebang, script_text):
    #         yield res

    # Monkey patch the existing setuptools class "ScriptWriter". While there
    # exist alternatives, this currently appears to be the most robust approach
    # for maintaining backward compatibility with older setuptools versions.
# `betse`-specific script writer for `setuptools`.
    # Replace the default "setuptools" class for writing scripts with ours.
#     easy_install.get_script_args = ScriptWriterSimple.get_script_args
#
# # ....................{ WRITER                             }....................
# class ScriptWriterSimple(ScriptWriter):
#     '''
#     Write Python script wrappers suitable for use with system-wide installations
#     of Python packages (e.g., via the `betse`-specific `symlink` command).
#
#     The default `ScriptWriter` class provided by `setuptools` writes Python
#     script wrappers attempting to import the `pkg_resources` for the
#     corresponding Python package. Since no `pkg_resources` are installed for
#     system-wide installations, such scripts *always* fail, implying such scripts
#     to be suitable *only* for use with user-specific venvs.
#
#     This class corrects such deficiency, albeit at a minor cost of ignoring the
#     `pkg_resources` for Python packages installed in the customary way.
#     '''
#
#     @classmethod
#     def get_script_args(
#         cls,
#         distribution: Distribution,
#         executable = easy_install.sys_executable,
#         wininst = False):
#         '''
#         Yield write_script() argument tuples for a distribution's entry points.
#         '''
#         # Class with which to write such scripts.
#         gen_class = cls.get_writer(wininst)
#
#         # Shebang line prefixing the contents of all such scripts.
#         script_shebang = easy_install.get_script_header("", executable, wininst)
#
#         # For each such script...
#         for script_basename, script_type, entry_point in\
#             util.package_distribution_entry_points(distribution):
#             # Script contents, formatted according to such template.
#             script_text = SCRIPT_TEMPLATE.format(
#                 entry_point_module = entry_point.module_name,
#                 entry_point_func = entry_point.attrs[0],
#             )
#
#             # Yield a tuple containing such metadata to the caller.
#             for res in gen_class._get_script_args(
#                 script_type, script_basename, script_shebang, script_text):
#                 yield res

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
