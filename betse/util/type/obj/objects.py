#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level object facilities.
'''

# ....................{ IMPORTS                            }....................
import inspect, platform
from betse.exceptions import BetseMethodException, BetseTypeException
from betse.util.type.types import (
    type_check, CallableTypes, CallableOrNoneTypes, ClassType, GeneratorType)

# ....................{ EXCEPTIONS                         }....................
@type_check
def die_unless_instance(obj: object, cls: ClassType) -> None:
    '''
    Raise an exception unless the passed object is an instance of the passed
    class.

    Parameters
    ----------
    obj : object
        Object to be validated.
    cls : ClassType
        Class to be validated.
    '''

    if not isinstance(obj, cls):
        raise BetseTypeException(
            'Object {!r} not an instance of class {!r}'.format(obj, cls))

# ....................{ TESTERS                            }....................
@type_check
def is_method(obj: object, method_name: str) -> bool:
    '''
    ``True`` only if the passed object has a method with the passed name.

    Parameters
    ----------
    obj : object
        Object to test for this method.
    method_name : str
        Name of the method to test this object for.

    Returns
    ----------
    bool
        `True` only if a method with this name is bound to this object.
    '''

    # Attribute with this name in this object if any or None otherwise.
    method = getattr(obj, method_name, None)

    # Return whether this attribute is a method.
    return callable(method)

# ....................{ TESTERS ~ pure                     }....................
# Tester distinguishing pure-Python from C-based class instances. Doing so is
# surprisingly non-trivial and, indeed, technically feasible with 100% accuracy
# *ONLY* under the official CPython interpreter. Why? Because the most accurate
# means of portably implementing this test in a cross-interpreter manner is to
# test whether the passed class instance defines the reserved "__dict__" or
# "__slots__" attributes. Whereas all pure-Python class instances are guaranteed
# to declare one or the other, most C-based class instances define neither. Of
# course, "most" is hardly "all." A C-based class may optionally request a
# "__dict__" attribute via "tp_dictoffset", resulting in false negatives in
# uncommon edge cases.
#
# If *NOT* running under the official CPython interpreter, this is the strongest
# possible implementation of this test; if running under the official CPython
# interpreter, however, this implementation may be strengthened by detecting
# whether or not the class of the passed class instance is a "heap type" (as
# defined by the "_Py_TPFLAGS_HEAPTYPE" docstring below). Only pure-Python
# classes are heap types, preserving a one-to-one correspondence between tester
# results and underlying interpreter reality.
#
# If the active Python interpreter is the official CPython implementation,
# prefer a more reliable CPython-specific solution guaranteed to succeed. Note
# that, to avoid circular import dependencies, this conditional unavoidably
# duplicates the existing betse.util.py.interpreters.is_cpython() tester.
if platform.python_implementation() == 'CPython':
    _Py_TPFLAGS_HEAPTYPE = (1<<9)
    '''
    Magic number defined by the `Include/object.h` C header in the official
    CPython codebase.

    CPython ORs the `__flags__` bit field of the class object for each **heap
    type** (i.e., pure-Python class whose type structure is dynamically
    allocated at interpreter runtime rather than a C-based class whose type
    structure is statically preallocated at either interpreter or C extension
    compile time).
    '''

    # To reduce duplication, this tester's docstring is dynamically set below.
    @type_check
    def is_pure_python(obj: object) -> bool:

        # If the passed object is *NOT* a class, this object *MUST* be a class
        # instance. (By Python 3.x design, all objects -- including primitive
        # builtins such as "int" and "bool" -- are one or the other). In this
        # case, obtain the class this instance is an instance of.
        cls = obj if isinstance(obj, type) else type(obj)

        # Return True only if this class is a heap type, as indicated by its
        # heap type bit flag being non-zero.
        return bool(cls.__flags__ & _Py_TPFLAGS_HEAPTYPE)
# Else, fallback to a CPython-agnostic solution typically but *NOT* necessarily
# succeeding. For all real-world objects of interest, this is effectively
# successful. Edge cases exist but are suitably rare. See the commentary above.
else:
    # To reduce duplication, this tester's docstring is dynamically set below.
    @type_check
    def is_pure_python(obj: object) -> bool:

        # If the passed object is a class, return True only if this class
        # defines either the "__dict__" or "__slots__" attributes.
        # Unfortunately, the trivial test "hasattr(cls, '__dict__')" does *NOT*
        # suffice to decide whether this class defines the "__dict__" attribute.
        # Why? Because this attribute unconditionally exists for *ALL* classes,
        # pure-Python and C-based alike. Hence:
        #
        #     >>> hasattr(int, '__dict__')
        #     True
        #
        # For unknown and presumably banal reasons, the dir() builtin strips the
        # "__dict__" attribute name from its returned list only for C-based
        # classes. Hence, detecting whether a class is pure-Python or C-based in
        # a cross-interpreter manner reduces to iteratively searching the list
        # returned by dir() for this name.
        #
        # This constraint does *NOT* extend to the "__slots__" attribute, which
        # exists if and only if this class explicitly defines this attribute.
        # Are we having fun yet?
        if isinstance(obj, type):
            return '__dict__' in dir(obj) or hasattr(obj, '__slots__')
        # Else, this object *MUST* be a class instance. In this case, return
        # True only if similar conditions hold. Since a class instance defines
        # the "__dict__" attribute only if this instance is a pure-Python
        # instance whose class does *NOT* define the "__slots__" attribute, this
        # conditional may efficiently lookup the "__dict__" attribute directly
        # rather than inefficiently defer to the dir() builtin. It is fun!
        else:
            return hasattr(obj, '__dict__') or hasattr(obj, '__slots__')

# Docstring dynamically set for the tester defined above.
is_pure_python.__doc__ = '''
``True`` if the passed object is either a pure-Python class or instance of such
a class *or* ``False`` otherwise (i.e., if this object is either a C-based class
or instance of such a class, either builtin or defined by a C extension,).

Parameters
----------
obj : object
    Object to be tested.

Returns
----------
bool
    ``True`` only if this object is a pure-Python class _or_ instance of such a
    class.

See Also
----------
https://stackoverflow.com/a/41012823/2809027
    Stackoverflow answer strongly inspiring this implementation.
'''


def is_c_based(obj: object) -> bool:
    '''
    ``True`` if the passed object is either a C-based class or instance of such a
    class (either builtin or defined by a C extension) *or* ``False`` otherwise
    (i.e., if this object is either a pure-Python class or instance of such a
    class).

    Parameters
    ----------
    obj : object
        Object to be tested.

    Returns
    ----------
    bool
        ``True`` only if this object is a C-based class _or_ instance of such a
        class.
    '''

    return not is_pure_python(obj)

# ....................{ GETTERS                            }....................
@type_check
def get_method(obj: object, method_name: str) -> CallableTypes:
    '''
    Method with the passed name bound to the passed object.

    Parameters
    ----------
    obj : object
        Object to obtain this method from.
    method_name : str
        Name of the method to be obtained.

    Returns
    ----------
    CallableTypes
        Method with this name bound to this object.

    Raises
    ----------
    BetseMethodException
        If no such method is bound to this object.
    '''

    # Attribute with this name in this object if any or None otherwise.
    method = getattr(obj, method_name, None)

    # If no such attribute exists, raise an exception.
    if method is None:
        raise BetseMethodException('Method {}.{}() undefined.'.format(
            obj.__class__.__name__, method_name))

    # If such an attribute exists but is *NOT* a method, raise an exception.
    if not callable(method):
        raise BetseMethodException(
            'Object attribute "{}.{}" not a method: {!r}'.format(
            obj.__class__.__name__, method_name, method))

    # Else, this attribute is a method. Return this method as is.
    return method


@type_check
def get_method_or_none(obj: object, method_name: str) -> CallableOrNoneTypes:
    '''
    Method with the passed name bound to the passed object if any *or* ``None``
    otherwise.

    Parameters
    ----------
    obj : object
        Object to obtain this method from.
    method_name : str
        Name of the method to be obtained.

    Returns
    ----------
    CallableOrNoneTypes
        Method with this name bound to this object if any *or* ``None``
        otherwise.
    '''

    # Attribute with this name in this object if any or None otherwise.
    method = getattr(obj, method_name, None)

    # If this attribute is a method, return this attribute; else, return None.
    return method if method is not None and callable(method) else None

# ....................{ ITERATORS ~ methods                }....................
def iter_methods(obj: object) -> GeneratorType:
    '''
    Generator yielding a 2-tuple of the name and value of each method bound to
    the passed object (in ascending lexicographic order of method name).

    This includes:

    * All methods statically registered in this object's internal dictionary
      (e.g., ``__dict__`` in unslotted objects), including both:
      * Builtin methods, whose names are both prefixed and suffixed by ``__``.
      * Custom methods, whose names are *not* prefixed and suffixed by ``__``.
    * All methods dynamically returned by **property methods** (i.e., methods
      decorated by the :func:`property` decorator).

    This excludes:

    * All property methods themselves.
    * All methods dynamically defined by this object's ``__getattr__()`` method
      or related runtime magic, which cannot (by definition) be inspected by
      this generator.

    Parameters
    ----------
    obj : object
        Object to iterate all methods of.

    Yields
    ----------
    (method_name, method_value)
        2-tuple of the name and value of each method bound to this object (in
        ascending lexicographic order of method name).

    Raises
    ----------
    Exception
        If any method of this object is a property whose
        :func:`property`-decorated method raises an exception. To avoid handling
        such exceptions, consider instead calling the
        :func:`iter_methods_custom_simple` generator excluding all properties.
    '''

    # For the name and value of each attribute of this object...
    for method_name, method_value in inspect.getmembers(obj):
        # If this attribute is a method, yield this name and value.
        if callable(method_value):
            yield method_name, method_value


@type_check
def iter_methods_matching(
    obj: object, predicate: CallableTypes) -> GeneratorType:
    '''
    Generator yielding 2-tuples of the name and value of each method bound to
    the passed object whose method name matches the passed predicate (in
    ascending lexicographic order of method name).

    Parameters
    ----------
    obj : object
        Object to yield all matching methods of.
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

    # For the name and value of each method of this object...
    for method_name, method_value in iter_methods(obj):
        # If this method matches this predicate, yield this name and value.
        if predicate(method_name):
            yield method_name, method_value


def iter_methods_custom(obj: object) -> GeneratorType:
    '''
    Generator yielding 2-tuples of the name and value of each **non-builtin
    method** (i.e., method whose name is *not* both prefixed and suffixed by
    `__`) bound to the passed object (in ascending lexicographic order of
    method name).

    Parameters
    ----------
    obj : object
        Object to yield all non-builtin methods of.

    Yields
    ----------
    (method_name, method_value)
        2-tuple of the name and value of each non-builtin method bound to this
        object (in ascending lexicographic order of method name).

    See Also
    ----------
    :func:`iter_methods`
        Further details.
    '''

    yield from iter_methods_matching(
        obj=obj, predicate=lambda method_name: not (
            method_name.startswith('__') and method_name.endswith('__')))

# ....................{ ITERATORS ~ vars                   }....................
def iter_vars(obj: object) -> GeneratorType:
    '''
    Generator yielding a 2-tuple of the name and value of each variable bound to
    the passed object (in ascending lexicographic order of variable name).

    This includes:

    * All variables statically registered in this object's internal dictionary
      (e.g., ``__dict__`` in unslotted objects), including both:
      * Builtin variables, whose names are both prefixed and suffixed by ``__``.
      * Custom variables, whose names are *not* prefixed and suffixed by ``__``.
    * All variables dynamically returned by **property methods** (i.e., methods
      decorated by the :func:`property` decorator).

    This excludes *only* variables dynamically defined by this object's
    ``__getattr__()`` method or related runtime magic, which cannot (by
    definition) be inspected by this generator.

    Parameters
    ----------
    obj : object
        Object to iterate the variables of.

    Yields
    ----------
    (var_name, var_value)
        2-tuple of the name and value of each variable bound to this object (in
        ascending lexicographic order of variable name).

    Raises
    ----------
    Exception
        If any variable of this object is a property whose
        :func:`property`-decorated method raises an exception. To avoid handling
        such exceptions, consider instead calling the
        :func:`iter_vars_simple_custom` generator excluding all properties.
    '''

    # For the name and value of each attribute of this object...
    for var_name, var_value in inspect.getmembers(obj):
        # If this attribute is *NOT* a method, yield this name and value.
        if not callable(var_value):
            yield var_name, var_value



def iter_vars_custom(obj: object) -> GeneratorType:
    '''
    Generator yielding 2-tuples of the name and value of each **non-builtin
    variable** (i.e., variable whose name is *not* both prefixed and suffixed by
    `__`) bound to the passed object (in ascending lexicographic order of
    variable name).

    Parameters
    ----------
    obj : object
        Object to yield all non-builtin variables of.

    Yields
    ----------
    (var_name, var_value)
        2-tuple of the name and value of each non-builtin variable bound to this
        object (in ascending lexicographic order of variable name).

    See Also
    ----------
    :func:`iter_vars`
        Further details.
    '''

    # For the name and value of each variable of this object...
    for var_name, var_value in iter_vars(obj):
        # If this variable is *NOT* builtin, yield this name and value.
        if not (var_name.startswith('__') and var_name.endswith('__')):
            yield var_name, var_value


#FIXME: For orthogonality, rename to iter_vars_custom_simple().
def iter_vars_simple_custom(obj: object) -> GeneratorType:
    '''
    Generator yielding 2-tuples of the name and value of each **non-builtin
    non-property variable** (i.e., variable whose name is *not* both prefixed
    and suffixed by ``__`` and whose value is *not* dynamically defined by the
    `@property` decorator to be the implicit result of a method call) bound to
    the passed object (in ascending lexicographic order of variable name).

    Only variables statically registered in this object's internal dictionary
    (e.g., ``__dict__`` in unslotted objects) are yielded. Variables dynamically
    defined by this object's ``__getattr__()`` method or related runtime magic
    are simply ignored.

    Parameters
    ----------
    obj : object
        Object to yield all non-builtin non-property variables of.

    Yields
    ----------
    (var_name, var_value)
        2-tuple of the name and value of each non-builtin non-property variable
        bound to this object (in ascending lexicographic order of variable
        name).
    '''

    # Ideally, this function would be reimplemented in terms of the iter_vars()
    # function calling the canonical inspect.getmembers() function. Dynamic
    # inspection is surprisingly non-trivial in the general case, particularly
    # when virtual base classes rear their diamond-studded faces. Moreover,
    # doing so would support edge-case attributes when passed class objects,
    # including:
    #
    # * Metaclass attributes of the passed class.
    # * Attributes decorated by "@DynamicClassAttribute" of the passed class.
    #
    # Sadly, inspect.getmembers() internally accesses attributes via the
    # dangerous getattr() builtin rather than the safe inspect.getattr_static()
    # function. This function explicitly requires the latter and hence *MUST*
    # reimplement rather than defer to inspect.getmembers(). (Sadness reigns.)
    #
    # For the same reason, the unsafe vars() builtin cannot be called either.
    # Since that builtin fails for builtin containers (e.g., "dict", "list"),
    # this is not altogether a bad thing.
    for var_name in dir(obj):
        # If this attribute is *NOT* a builtin...
        if not (var_name.startswith('__') and var_name.endswith('__')):
            # Value of this attribute guaranteed to be statically rather than
            # dynamically retrieved. The getattr() builtin performs the latter,
            # dynamically calling this attribute's getter if this attribute is
            # a property. Since that call could conceivably raise unwanted
            # exceptions *AND* since this function explicitly ignores
            # properties, static attribute retrievable is unavoidable.
            var_value = inspect.getattr_static(obj, var_name)

            # If this value is neither callable nor a property, this attribute
            # is a non-property variable. Yield this variable.
            if not (callable(var_value) or isinstance(var_value, property)):
                yield var_name, var_value