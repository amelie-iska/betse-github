#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level object facilities.
'''

# ....................{ IMPORTS                            }....................
from betse.exceptions import BetseTypeException
from betse.util.type.types import (
    type_check,
    CallableTypes,
    ClassType,
    GeneratorType,
    MappingType,
    SequenceTypes,
)

# ....................{ EXCEPTIONS                         }....................
@type_check
def die_unless_subclass(subclass: ClassType, superclass: ClassType) -> None:
    '''
    Raise an exception unless the first passed class inherits and is thus a
    subclass of the second passed class.

    Parameters
    ----------
    subclass : ClassType
        Subclass to be validated.
    superclass : ClassType
        Superclass to be validated.
    '''

    if not issubclass(subclass, superclass):
        raise BetseTypeException(
            'Class {!r} not a subclass of class {!r}'.format(
                subclass, superclass))

# ....................{ ITERATORS                          }....................
@type_check
def iter_methods(cls: ClassType) -> GeneratorType:
    '''
    Generator yielding a 2-tuple of the name and value of each method defined by
    the passed class (in ascending lexicographic order of method name).

    This generator *only* yields methods statically registered in the internal
    dictionary for this class (e.g., ``__dict__`` in unslotted classes),
    including:

    * Builtin methods, whose names are both prefixed and suffixed by ``__``.
    * Custom methods, whose names are *not* prefixed and suffixed by ``__``,
      including:
      * Custom standard methods.
      * Custom property methods (i.e., methods decorated by the builtin
        :func:`property` decorator).

    Parameters
    ----------
    cls : ClassType
        Class to iterate all methods of.

    Yields
    ----------
    (method_name, method_value)
        2-tuple of the name and value of each method bound to this object (in
        ascending lexicographic order of method name).
    '''

    # Avoid circular import dependencies.
    from betse.util.type.obj import objects

    # Well, isn't that special?
    yield from objects.iter_methods(cls)


@type_check
def iter_methods_matching(
    cls: ClassType, predicate: CallableTypes) -> GeneratorType:
    '''
    Generator yielding 2-tuples of the name and value of each method defined by
    the passed class whose method name matches the passed predicate (in
    ascending lexicographic order of method name).

    Parameters
    ----------
    cls: ClassType
        Class to yield all matching methods of.
    predicate : CallableTypes
        Callable iteratively passed the name of each method bound to this
        object, returning ``True`` only if that name matches this predicate.

    Yields
    ----------
    (method_name, method_value)
        2-tuple of the name and value of each matching method bound to this
        object (in ascending lexicographic order of method name).

    See Also
    ----------
    :func:`iter_methods`
        Further details.
    '''

    # Avoid circular import dependencies.
    from betse.util.type.obj import objects

    # Well, isn't that special?
    yield from objects.iter_methods_matching(cls)

# ....................{ DEFINERS                           }....................
@type_check
def define_class(
    class_name: str,
    class_attr_name_to_value: MappingType = {},
    base_classes: SequenceTypes = (),
) -> ClassType:
    '''
    Dynamically define a new class with the passed name subclassing all passed
    base classes and providing all passed class attributes (e.g., class
    variables, methods).

    Parameters
    ----------
    class_name : str
        Name of the class to be created.
    class_attr_name_to_value : MappingType
        Mapping from the name to the initial value of each class attribute
        (e.g., class variable, method) to declare this class to contain.
        Defaults to the empty dictionary, equivalent to declaring a class with
        the trivial body ``pass``.
    base_classes : optional[SequenceTypes]
        Sequence of all base classes to subclass this class from. Defaults to
        the empty tuple, equivalent to the 1-tuple ``(object,)`` containing only
        the root base class of all classes.

    Returns
    ----------
    ClassType
        Class dynamically defined with this name from these base classes and
        class attributes.
    '''

    # Thank you, bizarre 3-parameter variant of the type.__init__() method.
    return type(class_name, base_classes, class_attr_name_to_value)