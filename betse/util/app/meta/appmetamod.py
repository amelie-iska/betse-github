#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2019 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
High-level **application dependency metadata** (i.e., lists of version-pinned
dependencies synopsizing application requirements) functionality.
'''

# ....................{ IMPORTS                           }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To avoid race conditions during setuptools-based installation, this
# module may import *ONLY* from modules guaranteed to exist at the start of
# installation. This includes all standard Python and application modules but
# *NOT* third-party dependencies, which if currently uninstalled will only be
# installed at some later time in the installation. Likewise, to avoid circular
# import dependencies, the top-level of this module should avoid importing
# application modules where feasible.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# from betse.util.io.log import logs
from betse.util.type.types import (
    type_check,
    MappingType,
    MappingOrNoneTypes,
    ModuleType,
    IterableTypes,
    StrOrNoneTypes,
)

# ....................{ MAKERS                            }....................
@type_check
def merge_module_metadeps(
    module_name: str, modules_metadeps: IterableTypes) -> ModuleType:
    '''
    Dynamically create and return a new **application dependency metadata
    module** (i.e., module satisfying the informal protocol defined by the
    :mod:`betse.metadeps` module) with the passed name, iteratively merging the
    contents of all passed application dependency metadata modules.

    Specifically, this function (in order):

    #. Dynamically creates a new module with the passed name.
    #. For each of the global attributes assumed by the application dependency
       metadata protocol (i.e., dictionaries named ``RUNTIME_MANDATORY``,
       ``RUNTIME_OPTIONAL``, ``TESTING_MANDATORY``, and
       ``REQUIREMENT_NAME_TO_COMMANDS``), creates a new global attribute of the
       same name in this new module whose value is a dictionary merging the
       contents of all dictionaries of the same name defined by all passed
       modules. For example, if passed the :mod:`betse.metadeps` and
       :mod:`betsee.guimetadeps` modules, this function creates a new module
       defining a global dictionary named ``RUNTIME_MANDATORY`` merging the
       contents of the :attr:`betse.metadeps.RUNTIME_MANDATORY` and
       :mod:`betsee.guimetadeps.RUNTIME_MANDATORY` dictionaries.
    #. Returns this new module.

    Motivation
    ----------
    This utility function is *only* intended to be called by subclass
    implementations of the abstract private
    :meth:`betse.util.app.meta.appmetaabc.AppMetaABC._module_metadeps` property
    in downstream consumers. Notably, BETSEE calls this function from its
    concrete implementation of this property to merge its own dependency
    requirements with those of BETSE; doing so guarantees that calls to
    dependency-based functions within the BETSE codebase (e.g., of the
    :func:`betse.lib.libs.import_runtime_optional` function dynamically
    importing one or more optional dependencies) behave as expected.

    Caveats
    ----------
    **Order is insignificant.** If any of the requisite global dictionaries
    defined by any of the passed modules contain one or more keys contained in
    any other dictionary of the same name defined by any other passed module,
    this function raises an exception. Since this prevents any key collisions,
    *no* implicit precedence exists between these modules.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of the module to be created.
    modules_metadeps : IterableTypes
        Iterable of all application dependency metadata modules to be merged.
        Order is insignificant. See above.

    Raises
    ----------
    BetseAttrException
        If one or more of these modules fail to define one or more of the
        requisite attributes.
    BetseTypeException
        If one or more of these modules define one or more of the requisite
        attributes to be non-dictionaries.
    BetseModuleException
        If a module with this module name already exists.

    Returns
    ----------
    ModuleType
        Output application dependency metadata module with this name, merging
        the contents of these input application dependency metadata modules.
    '''

    # Avoid circular import dependencies.
    from betse.util.type.iterable import itertest
    from betse.util.type.obj import objects

    # If any of the passed modules is *NOT* a module, raise an exception.
    itertest.die_unless_items_instance_of(
        iterable=modules_metadeps, cls=ModuleType)

    # Dictionary mapping from the name to value of each module-scoped
    # attribute to be declared in the module to be created and returned.
    module_attr_name_to_value = {}

    # Tuple of the names of all global dictionaries required to be defined by
    # these input application dependency metadata modules.
    module_dicts_name = (
        'RUNTIME_MANDATORY',
        'RUNTIME_OPTIONAL',
        'TESTING_MANDATORY',
        'REQUIREMENT_NAME_TO_COMMANDS',
    )

    # For the name of each such global dictionary...
    for module_dict_name in module_dicts_name:
        # Generator comprehension aggregating all of the global dictionaries
        # defined by all of these input modules, raising exceptions if any such
        # module fails to define such a dictionary.
        modules_dict = (
            objects.get_attr(
                obj=modules_metadep,
                attr_name=module_dict_name,
                attr_type=MappingType,
            )
            for modules_metadep in modules_metadeps
        )

        #FIXME: Call the newly refactored
        #betse.util.type.iterable.mapping.mapmerge.merge_maps() function here.
        #Note that, as "on_collision=MergeCollisionType.RAISE_EXCEPTION" is the
        #default, no further work should be required.
        module_attr_name_to_value[module_dict_name] = None
