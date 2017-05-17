#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level module facilities.
'''

# ....................{ IMPORTS                            }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To raise human-readable exceptions on missing mandatory dependencies,
# the top-level of this module may import *ONLY* from packages guaranteed to
# exist at installation time -- which typically means *ONLY* BETSE packages and
# stock Python packages.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import collections, importlib, sys
from betse.exceptions import BetseModuleException
from betse.util.io.log import logs
from betse.util.type import types
from betse.util.type.types import (
    type_check,
    ModuleType,
    ModuleOrStrTypes,
    SetType,
    StrOrNoneTypes,
)
from importlib import util as importlib_util
from importlib.machinery import ExtensionFileLoader, EXTENSION_SUFFIXES

# ....................{ GLOBALS ~ dict                     }....................
MODULE_TO_VERSION_ATTR_NAME = collections.defaultdict(
    # Default attribute name to be returned for all unmapped modules.
    lambda: '__version__',

    # Module-specific attribute names.
    PIL = 'PILLOW_VERSION',
)
'''
Dictionary mapping the fully-qualified name of a module or package (e.g.,
:mod:``PIL``) to the name of the attribute (e.g., ``PILLOW_VERSION``) declared
by that module or package, providing that module or package's version specifier.

All modules and packages unmapped by this dictionary default to the canonical
``__version__`` attribute name.
'''

# ....................{ EXCEPTIONS                         }....................
@type_check
def die_unless_module(
    module_name: str, exception_message: StrOrNoneTypes = None) -> None:
    '''
    Raise an exception with the passed message (defaulting to a message
    synthesized from the passed module name) if the module with the passed name
    is *not* importable by the active Python interpreter.

    If this module is a **submodule** (i.e., if this module's name contains one
    or more `.` characters), all transitive parent packages of this module will
    be iteratively imported as an unavoidable side effect of this function call.
    '''

    # If this module is unimportable, raise an exception.
    if not is_module(module_name):
        # If no exception message was passed, synthesize one from this name.
        if not exception_message:
            exception_message = 'Module "{}" not found.'.format(module_name)

        # Raise this exception. To permit callers to transparently handle
        # importation errors in the conventional way, raise the conventional
        # exception rather than a BETSE-specific exception (e.g.,
        # "BetseModuleException").
        raise ImportError(exception_message)

# ....................{ TESTERS                            }....................
@type_check
def is_module(module_name: str) -> bool:
    '''
    ``True`` only if the module with the passed fully-qualified name is
    importable under the active Python interpreter.

    If this module is a **submodule** (i.e., contains a ``.`` character), all
    parent modules of this module will be imported as a side effect of this
    function call. Likewise, if this module is _not_ importable via standard
    mechanisms (e.g., the OS X-specific :mod:`PyObjCTools` package), the module
    itself may also be imported as a side effect.
    '''

    # Depending on context, this function behaves in one of three distinct ways:
    #
    # * If this module's name is a key in the canonical dictionary "sys.modules"
    #   and has thus already been imported at least once under the current
    #   process, then...
    #   * If the "sys.modules[module_name].__spec__" attribute is set to a non-
    #     None value, such value is returned.
    #   * Else, the "ValueError" exception is raised.
    # * Else if this module is loadable by iteratively querying all module
    #   loaders in "sys.meta_path" (the canonical list of such loaders), a new
    #   spec is created describing this module and returned.
    # * Else, None is returned.
    #
    # Since this function only returns a single boolean, such return values and
    # exceptions are converted to simple boolean values.
    try:
        return importlib_util.find_spec(module_name) is not None
    # Unfortunately, this exception does *NOT* necessarily imply this module to
    # not exist. This module may exist even if this exception is thrown,
    # particularly for modules defined dynamically at runtime rather than loaded
    # from an external file. Further inspection is warranted.
    #
    # Unfortunately, this exception does imply that conventional alternatives to
    # the prior function call (e.g., testing tuples generated by
    # pkgutil.iter_modules()) will also fail to find this module. As a fallback,
    # attempt to manually import this module. Since doing so implicitly imports
    # the "__init__.py" files of all parent packages of this module and hence
    # may have unhelpful side effects, we do so only if the prior call failed.
    except ValueError:
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False


@type_check
def is_imported(*module_names: str) -> bool:
    '''
    ``True`` only if all modules with the passed fully-qualified names have
    already been imported under the current Python process.
    '''

    # all(). It is awesome.
    return all(module_name in sys.modules for module_name in module_names)

# ....................{ TESTERS ~ type                     }....................
#FIXME: Add unit tests, as this is a fairly fragile tester.
@type_check
def is_c_extension(module: ModuleOrStrTypes) -> bool:
    '''
    ``True`` only if the passed module is a C extension implemented as a
    dynamically linked shared library specific to the current platform.

    Parameters
    ----------
    module : ModuleOrStrTypes
        Either:
        * The fully-qualified name of this module, in which case this function
          dynamically imports this module.
        * A previously imported module object.

    Returns
    ----------
    bool
        ``True`` only if this module is a C extension.
    '''

    # Avoid circular import dependencies.
    from betse.util.path import pathnames

    # Resolve this module's object.
    module = _resolve_module(module)

    # If this module was loaded by a PEP 302-compliant C extension loader, this
    # module *MUST* be a C extension.
    if isinstance(getattr(module, '__loader__', None), ExtensionFileLoader):
        return True

    # Else, fallback to filetype matching heuristics.
    #
    # Absolute path of the file defining this module.
    module_filename = get_filename(module)

    # "."-prefixed filetype of this path if any or "None" otherwise.
    module_filetype = pathnames.get_filetype_dotted_or_none(module_filename)
    # print('module_filetype: {}'.format(module_filetype))

    #FIXME: Mildly inefficient, as "EXTENSION_SUFFIXES" is a list rather than a
    #set. Since this list is small *AND* since this function is called
    #infrequently, this is currently ignorable. The trivial fix is to define a
    #new private "_EXTENSION_SUFFIXES = set(EXTENSION_SUFFIXES)" global above
    #and leverage that here instead.

    # This module is only a C extension if this path's filetype is that of a
    # C extension specific to the current platform.
    return module_filetype in EXTENSION_SUFFIXES

# ....................{ GETTERS ~ path                     }....................
@type_check
def get_dirname(module: ModuleOrStrTypes) -> str:
    '''
    Absolute path of the directory containing the file providing the passed
    module or package.

    Parameters
    ----------
    module : ModuleOrStrTypes
        Either:
        * The fully-qualified name of this module, in which case this function
          dynamically imports this module.
        * A previously imported module object.

    Returns
    ----------
    str
        Absolute path of this directory.
    '''

    # Avoid circular import dependencies.
    from betse.util.path import pathnames

    # Return this dirname.
    return pathnames.get_dirname(get_filename(module))


#FIXME: The current approach is trivial and therefore terrible, breaking down
#under commonplace real-world conditions (e.g., modules embedded within egg-like
#archives). Consider generalizing this approach via the new setuptools-based
#"betse.lib.setuptool.resources" submodule.
@type_check
def get_filename(module: ModuleOrStrTypes) -> str:
    '''
    Absolute path of the file providing the passed module or package.

    If the passed object signifies:

    * A package (e.g., directory), this is the absolute path of the file
      providing this package's ``__init__`` submodule.
    * A non-package (e.g., module, C extension), this is the absolute path of
      the file providing this non-package as is.

    Caveats
    ----------
    Since effectively *all* modules and packages (except in-memory builtin
    modules) are associated with a corresponding file, there intentionally
    exists no corresponding ``get_filename_or_none()`` function.

    Since *only* packages define the ``__path__`` attribute, there likewise
    exists no corresponding ``get_pathname()`` function. Only the ``__file__``
    attribute retrieved by this function is generally applicable to *all*
    modules and packages regardless of type.

    Parameters
    ----------
    module : str or ModuleType
        Either:
        * The fully-qualified name of this module, in which case this function
          dynamically imports this module.
        * A previously imported module object.

    Returns
    ----------
    str
        Absolute path of this file.

    Raises
    ----------
    BetseModuleException
        If this module has no ``__file__`` attribute (e.g., is a builtin
        module).
    '''

    # Resolve this module's object.
    module = _resolve_module(module)

    # If this module provides the special "__file__" attribute, test this
    # attribute. Technically, all modules *EXCEPT* builtin modules should
    # provide this attribute.
    if hasattr(module, '__file__'):
        return module.__file__

    # Else, raise an exception.
    raise BetseModuleException(
        'Module "{}.__file__" attribute not found '
        '(e.g., as "{}" is a builtin module).'.format(module.__name__))

# ....................{ GETTERS ~ global                   }....................
@type_check
def get_global_names(module: ModuleOrStrTypes) -> SetType:
    '''
    Set of the names of all global variables defined by the passed module.

    This function returns the set of the names of all attributes defined by this
    module, excluding:

    * Special attributes reserved for use by Python (e.g., ``__file__``).
    * Callable attributes (e.g., functions, lambdas).

    Parameters
    ----------
    module : ModuleOrStrTypes
        Either:
        * The fully-qualified name of this module, in which case this function
          dynamically imports this module.
        * A previously imported module object.

    Returns
    ----------
    set
        Set of the names of all global variables defined by this module.
    '''

    # Resolve this module's object.
    module = _resolve_module(module)

    # Return this set via a set comprehension.
    return {
        module_attr_name
        for module_attr_name in dir(module)
        if (
            (not module_attr_name.startswith('__')) and
            callable(getattr(module, module_attr_name))
        )
    }

# ....................{ GETTERS ~ version                  }....................
@type_check
def get_version(module: ModuleOrStrTypes) -> str:
    '''
    Version specifier of the passed module.

    If this module provides no version specifier, an exception is raised.

    See Also
    ----------
    :func:`get_version_or_none`
        Further details on the passed parameter.
    '''

    # Module version if any or "None" otherwise.
    module_version = get_version_or_none(module)

    # If this version does *NOT* exist, raise an exception.
    if module_version is None:
        raise BetseModuleException(
            'Module "{}" version not found.'.format(module))

    # Return this version.
    return module_version


@type_check
def get_version_or_none(module: ModuleOrStrTypes) -> StrOrNoneTypes:
    '''
    Version specifier of the passed module if that module provides a version
    specifier *or* ``None`` otherwise.

    Parameters
    ----------
    module : ModuleOrStrTypes
        Either:
        * The fully-qualified name of this module, in which case this function
          dynamically imports this module.
        * A previously imported module object.

    Returns
    ----------
    StrOrNoneTypes
        This module's version specifier if any *or* ``None`` otherwise.
    '''

    # Resolve this module's object.
    module = _resolve_module(module)

    # Name of the version specifier attribute defined by that module. For sane
    # modules, this is "__version__". Insane modules, however, exist.
    module_version_attr_name = MODULE_TO_VERSION_ATTR_NAME[module.__name__]

    # This attribute defined by this module if any or "None" otherwise.
    module_version = getattr(module, module_version_attr_name, None)

    # If this version is undefined, log a non-fatal warning.
    if module_version is None:
        logs.log_warning('Module "%s" version not found.', module.__name__)

    # Return this version.
    return module_version

# ....................{ IMPORTERS                          }....................
@type_check
def import_module(
    module_name: str, exception_message: StrOrNoneTypes = None) -> ModuleType:
    '''
    Dynamically import and return the module, package, or C extension with the
    passed fully-qualified name.

    If this module is unimportable, an exception with the passed message is
    raised.
    '''

    # If this module is unimportable, raise an exception.
    die_unless_module(module_name, exception_message)

    # Else, import and return this module.
    return importlib.import_module(module_name)

# ....................{ PRIVATE ~ resolvers                }....................
@type_check
def _resolve_module(module : ModuleOrStrTypes) -> ModuleType:
    '''
    Dynamically import and return the module with the passed name if a string
    is passed *or* return the passed module as is otherwise.

    This utility function is intended *only* to simplify the implementation of
    public functions defined by this submodule and is hence private.

    Parameters
    ----------
    module : ModuleOrStrTypes
        Either:
        * The fully-qualified name of this module, in which case this function
          dynamically imports this module.
        * A previously imported module object.

    Returns
    ----------
    ModuleType
        Module object resolved from the passed parameter.
    '''

    # If a module name was passed, dynamically import and return this module.
    if types.is_str(module):
        return import_module(module)
    # Else, type checking guarantees this object to be a module. Return this.
    else:
        return module
