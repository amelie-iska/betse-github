#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

#FIXME: We'll almost certainly want to modify the output ".spec" file to
#transparently detect the current OS and modify its behaviour accordingly.
#Happily, ".spec" files appear to be mostly Python. As a trivial example, see:
#    https://github.com/suurjaak/Skyperious/blob/master/packaging/pyinstaller.spec
#Also note the platform-specific instructions at:
#    http://irwinkwan.com/2013/04/29/python-executables-pyinstaller-and-a-48-hour-game-design-compo

#FIXME: Embed ".ico"-suffixed icon files in such executables. PyInstaller
#provides simple CLI options for this; we simply need to create such icons.
#Contemplating mascots, how about the ever-contemplative BETSE cow?
#
#Sadly, the icon formats required by OS X and Windows appear to conflict.
#Windows icon files have filetype ".ico" (and appear to support only one
#embedded icon), whereas OS X icon files have filetype ".icns" (and appear to
#support multiple embedded icons). To compound matters, "pyinstaller" provides
#only one option "--icon" for both, probably implying that we'll need to
#dynamically detect whether the current system is OS X or Windows and respond
#accordingly (i.e., by passing the appropriate system-specific icon file).

#FIXME: Executables output under OS X and Windows pretty much *MUST* be signed.
#This looks to be fairly trivial under Windows. OS X, however, is another kettle
#of hideous fish. In any case, everyone else has already solved this, so we just
#need to leverage the following detailed recipes:
#
#* https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Win-Code-Signing
#* https://github.com/pyinstaller/pyinstaller/wiki/Recipe-OSX-Code-Signing

#FIXME: Embed Windows-specific version metadata in such executables. This is a
#fairly bizarre process, which we've documented in "pyinstaller.yaml". It's
#hardly crucial for now, but will be important at some point.
#FIXME: Embed OS X-specific version metadata in such executables. We'll want to
#detect whether the current OS is OS X and, if so, manually overwrite the
#autogenerated "myapp.app/Contents/Info.plist" file with one of our own
#devising. Not terribly arduous... in theory.

#FIXME: Also make a "freeze_dir" class. Since such class is intended only for
#debugging, such class' run() method should also pass the "--debug" option to
#"pyinstaller".

#FIXME: Contribute back to the community. Contemplate a stackoverflow answer.
#(We believe we may have espied an unanswered question asking about query words
#"pyinstaller setuptools integration". Huzzah!) We should note that PyInstaller
#will probably be unable to find the imports of setuptools-installed scripts,
#due to the obfuscatory nature of such scripts. See the following for a
#reasonable solution:
#    https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Setuptools-Entry-Point

'''
`betse`-specific `freeze` commands for `setuptools`.
'''

# ....................{ IMPORTS                            }....................
from os import path
from setup import util
from setuptools import Command

# ....................{ COMMANDS                           }....................
def add_setup_commands(setup_options: dict) -> None:
    '''
    Add `freeze` commands to the passed dictionary of `setuptools` options.
    '''
    util.add_setup_command_classes(setup_options, freeze_file)

# ....................{ CLASSES                            }....................
class freeze_file(Command):
    '''
    Create one platform-specific executable file in the top-level `dist`
    directory for each previously installed script for the current application.

    Each such file is created by running PyInstaller's external command
    `pyinstaller` with sane command-line arguments. Since PyInstaller does *not*
    currently (and probably never will) support cross-bundling, such files are
    formatted specific to and hence executable *only* under the currenty
    operating system. Specifically:

    * Under Linux, such files will be ELF (Executable and Linkable Format)
      binaries.
    * Under OS X, such files will be conventional ".app"-suffixed directories.
      (Of course, that's not a file. So sue us.)
    * Under Windows, such files will be conventional ".exe"-suffixed binaries.

    Attributes
    ----------
    install_scripts_dir : str
        Absolute path of the directory to which all wrapper scripts were
        previously installed.
    '''

    description =\
        'freeze all installed scripts to platform-specific executable files'
    '''
    Command description printed when running `./setup.py --help-commands`.
    '''

    user_options = []
    '''
    List of 3-tuples specifying command-line options accepted by this command.
    '''

    def initialize_options(self):
        '''
        Declare option-specific attributes subsequently initialized by
        `finalize_options()`.

        If this function is *not* defined, the default implementation of this
        method raises an inscrutable `distutils` exception. If such attributes
        are *not* declared, the subsequent call to
        `self.set_undefined_options()` raises an inscrutable `setuptools`
        exception. (This is terrible. So much hate.)
        '''
        self.install_scripts_dir = None

    def finalize_options(self):
        '''
        Default undefined command-specific options to the options passed to the
        current parent command if any (e.g., `symlink`).
        '''
        # Copy the "install_dir" attribute from the existing "install_scripts"
        # attribute of a temporarily instantiated "symlink" object.
        #
        # Why? Because setuptools.
        self.set_undefined_options(
            'symlink', ('install_scripts', 'install_scripts_dir'))

    def run(self):
        '''Run the current command and all subcommands thereof.'''
        # If PyInstaller is not found, fail.
        util.die_unless_command(
            'pyinstaller',
            'PyInstaller not installed or "pyinstaller" not in the current PATH'
        )

        # If UPX is not found, print a warning to standard error. While
        # optional, freezing in the absence of UPX produces uncompressed and
        # hence considerably larger executables.
        if not util.is_command('upx'):
            util.output_warning(
                'UPX not installed or "upx" not in the current path. '
                'All frozen executables will be uncompressed.'
            )

        # Freeze each previously installed script wrapper.
        for script_basename, script_type, _ in util.command_entry_points(self):
            # Basename of the PyInstaller ".spec" file converting such
            # platform-independent script into a platform-specific executable.
            # To ensure such file is recreated and reused in the same directory
            # as the top-level "setup.py" script, such file's path is specified
            # as a basename and hence relative to such directory.
            script_spec_basename = '{}.spec'.format(script_basename)

            # If such ".spec" file exists, instruct PyInstaller to reuse rather
            # than recreate such file, thus preserving manual edits made to such
            # file following its prior creation.
            if util.is_file(script_spec_basename):
                print('Reusing spec file "{}".'.format(script_spec_basename))

                # Freeze such script with such ".spec" file. Note that
                # "pyinstaller" supports substantially command-line options
                # under this mode of operation than when passed a Python script.
                util.die_unless_command_succeeds(
                    'pyinstaller',

                    # Overwrite existing output paths under the "dist/" subdirectory
                    # without confirmation, the default behaviour.
                    '--noconfirm',

                    script_spec_basename,
                )
            # Else, instruct PyInstaller to (re)create such ".spec" file.
            else:
                print('Generating spec file "{}".'.format(script_spec_basename))

                # Absolute path of such script.
                script_filename = path.join(
                    self.install_scripts_dir, script_basename)
                util.die_unless_file(
                    script_filename, (
                        'Script "{}" not found. Consider first running either'
                        '"sudo python3 setup.py install" or '
                        '"sudo python3 setup.py symlink".'
                    ),
                )

                # Freeze such script without such ".spec" file.
                util.die_unless_command_succeeds(
                    'pyinstaller',
                    '--onefile',

                    # Overwrite existing output paths under the "dist/" subdirectory
                    # without confirmation, the default behaviour.
                    '--noconfirm',

                    # If this is a console script, configure standard input and
                    # output for console handling; else, do *NOT* and, if the
                    # current operating system is OS X, generate an ".app"-suffixed
                    # application bundle rather than a customary executable.
                    '--console' if script_type == 'console' else '--windowed',

                    script_filename,
                )

# --------------------( WASTELANDS                         )--------------------
    #FUXME: Does this actually work? If so, replicate to the other modules in
    #this package as well.

            # Basename of the PyInstaller ".spec" file converting such
            # platform-independent script into a platform-specific executable.
            # Since such file is specific to both the basename of such script
            # *AND* the type of the current operating system, such substrings
            # are embedded in such filename.
            # script_spec_basename = '{}.{}.spec'.format(
            #     script_basename, util.get_os_type())

                # # Basename of the currently generated spec file.
                # script_spec_basename_current = '{}.spec'.format(script_basename)
                #
                # # Rename such file to have the operating system-specific
                # # basename expected by the prior conditional (on the next
                # # invocation of this setuptools command).
                # #
                # # Note that "pyinstaller" accepts an option "--name" permitting
                # # the basename of such file to be specified prior to generating
                # # such file. Unfortunately, such option *ALSO* specifies the
                # # basename of the generated executable. Since we only
                # util.move_file(
                #     script_spec_basename_current, script_spec_basename)

                #FUXME: If a ".spec" file exists, such file should be passed rather
                #than such script's basename. Note that, when passing such file,
                #most CLI options are ignored; of those we use below, only
                #"--noconfirm" appears to still be respected.

                    # path.basename(script_spec_basename))
            # Absolute path of the PyInstaller ".spec" file converting such
            # platform-independent script into a platform-specific executable.
            # Since such file is specific to both the basename of such script
            # *AND* the type of the current operating system, such substrings
            # are embedded in such filename.
            # script_spec_filename = path.join(
            #     script_basename, util.get_os_type()
            # )

            # util.output_sans_newline(
            #     'Searching for existing spec file "{}"... '.format(
            #         path.basename(script_spec_filename)))
#".app"-suffixed
        # # List of shell words common to all "pyinstaller" commands called below.
        # command_words_base = [
        #     'pyinstaller',
        #     '--onefile',
        #     # Overwrite existing output paths under the "dist/" subdirectory
        #     # without confirmation, the default behaviour.
        #     '--noconfirm',
        # ]
            # command_words_base
            #
            # if script_type == 'console':
            #     --console
                # 'Disabling compression of output executables.'
# from setuptools.command.install import install
# from setuptools.command.install_lib import install_lib
# from setuptools.command.install_scripts import install_scripts
# from distutils.errors import DistutilsFileError
    # Class Design
    # ----------
    # Despite subclassing the `install_scripts` class, this class does *not*
    # install scripts. This class subclasses such class merely to obtain access to
    # metadata on installed scripts (e.g., installation directory).

#FUXME: We may need to actually subclass "install" instead. No idea. Just try
#accessing "self.install_dir" below. If that fails, try "self.install_scripts".
#If that fails, try subclassing "install" instead and repeating such access
#attempts. Yes, this sucks. That's setuptools for you.
