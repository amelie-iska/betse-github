#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
High-level **Python profiling** (i.e., measuring various metrics pertaining to
Python code, including time and space performance) facilities.
'''

# ....................{ IMPORTS                            }....................
from betse.util.io.log import logs
from betse.util.type.types import (
    type_check, CallableTypes, MappingType, SequenceTypes,)
from cProfile import Profile
from enum import Enum
from functools import partial
from io import StringIO
from pstats import Stats
from timeit import Timer

# ....................{ ENUMS                              }....................
ProfileType = Enum('ProfileType', ('NONE', 'CALL', 'LINE',))
'''
Enumeration of all possible types of profiling supported by the
:func:`profile_callable` function.

Attributes
----------
NONE : enum
    Null profiling. Callables profiled under this type of profiling will still
    be called as expected but will _not_ be profiled.
CALL : enum
    Call-granularity profiling of callables (e.g., functions, lambdas, methods,
    and `eval` statements). This level of granularity is more coarse-grained
    than that of the `LINE` type.
LINE : enum
    Line-granularity profiling of callables (e.g., functions, lambdas, methods,
    and `eval` statements). This level of granularity is more fine-grained than
    that of the `CALL` type.
'''

# ....................{ PROFILERS                          }....................
@type_check
def profile_callable(
    call: CallableTypes,
    args: SequenceTypes = None,
    kwargs: MappingType = None,
    is_profile_logged: bool = True,
    profile_filename: str = None,
    profile_type: ProfileType = ProfileType.CALL,
) -> object:
    '''
    Profile the passed callable with the passed positional and keyword arguments
    (if any), returning the value returned by this call and optionally logging
    and serializing the resulting profile to the file with the passed filename.

    Parameters
    ----------
    call : CallableTypes
        Callable to be timed.
    args : optional[SequenceTypes]
        Sequence of positional arguments to pass to the call to this callable.
        Defaults to `None`, in which no such arguments are passed.
    kwargs: optional[MappingType]
        Dictionary of keyword arguments to pass to the call to this callable.
        Defaults to `None`, in which no such arguments are passed.
    is_profile_logged : optional[bool]
        `True` only if logging the profile of this call _after_ this call.
        Defaults to `True`.
    profile_filename : optional[str]
        Absolute or relative path of the file to serialize this profile to. If
        this file already exists, this file will be silently overwritten
        _without_ explicit warning or error. (While silently overwriting is
        typically discouraged, doing so is sensible in this case. Profiles are
        frequently and trivially created, rendering their preservation
        insignificant by compare to usability concerns.)
        Defaults to `None`, in which case no such file is serialized.
    profile_type : optional[ProfileType]
        Type of profiling to perform. Defaults to :data:`ProfileType.CALL`, in
        which case call-granularity profiling is performed.

    Returns
    ----------
    object
        Value returned by this call.
    '''

    # Private module function performing this type of profiling. Due to type
    # checking, this type is guaranteed to be a valid key of this dictionary.
    profiler = _PROFILE_TYPE_TO_PROFILER[profile_type]

    # Default unpassed positional and keyword arguments.
    if   args is None:   args = ()
    if kwargs is None: kwargs = {}

    # Profile a call of this callable with this profiler, returning the value
    # that this call returns.
    return profiler(
        call=call,
        args=args,
        kwargs=kwargs,
        is_profile_logged=is_profile_logged,
        profile_filename=profile_filename,
    )


def _profile_callable_none(
    call, args, kwargs, is_profile_logged, profile_filename) -> object:
    '''
    Call the passed callable with the passed positional and keyword arguments
    _without_ profiling this call, returning the value returned by this call.

    See Also
    ----------
    :func:`profile_callable`
        Further details on function signature.
    '''

    return call(*args, **kwargs)


def _profile_callable_call(
    call, args, kwargs, is_profile_logged, profile_filename) -> object:
    '''
    Profile the passed callable in a call-oriented deterministic manner with the
    passed positional and keyword arguments (if any), returning the value
    returned by this call and optionally logging and serializing the resulting
    profile to the file with the passed filename.

    See Also
    ----------
    :func:`profile_callable`
        Further details on function signature.
    '''

    # Log this fact.
    logs.log_debug('Call-granularity profiling enabled.')

    # Call-granularity profile of the subsequent call to this callable.
    profile = Profile()

    # Value returned by calling this callable with these arguments, storing a
    # profile of this call into this "profile" object.
    return_value = profile.runcall(call, *args, **kwargs)

    # If the caller requested this profile be logged...
    if is_profile_logged:
        # Number of slowest callables to be logged. For sanity, the full list of
        # all profiled callables is truncated below to a sublist of this size.
        # For readability, this is currently twice the default number of rows in
        # the average Linux terminal.
        CALLABLE_COUNT = 48

        # String buffer describing these slowest callables.
        calls_sorted = StringIO()

        # Statistics harvested from this profile into this string buffer.
        calls = Stats(profile, stream=calls_sorted)

        # For readability, strip the dirnames from all pathnames in statistics
        # output, reducing these pathnames to basenames.
        calls.strip_dirs()

        # Sort all profiled callables by cumulative time (i.e., total time spent
        # in a callable including all time spent in calls to callables called by
        # that callable).
        calls.sort_stats('cumtime')

        # Write the slowest sublist of these callables to this string buffer.
        calls.print_stats(CALLABLE_COUNT)

        # Sort all profiled callables by "total" time (i.e., total time spent in
        # a callable excluding all time spent in calls to callables called by
        # that callable).
        calls.sort_stats('tottime')

        # Write the slowest sublist of these callables to this string buffer.
        calls.print_stats(CALLABLE_COUNT)

        # Log this string buffer.
        logs.log_info(
            'Slowest %d callables profiled by both '
            'cumulative and total time:\n%s',
            CALLABLE_COUNT, calls_sorted.getvalue())

    # If the caller requested this profile be serialized to a file...
    if profile_filename is not None:
        # Log this serialization.
        logs.log_info(
            'Writing Python-formatted profile to "%s".', profile_filename)

        # Serialize this profile to this file.
        profile.dump_stats(profile_filename)

    # Return the value returned by this call.
    return return_value


#FIXME: Consider implementing a non-deterministic alternative as well, which
#"pprofile" also supports via the "pprofile.StatisticalProfile" class.
def _profile_callable_line(
    call, args, kwargs, is_profile_logged, profile_filename) -> object:
    '''
    Profile the passed callable in a line-oriented deterministic manner with the
    passed positional and keyword arguments (if any), returning the value
    returned by this call and optionally logging and serializing the resulting
    profile to the file with the passed filename.

    See Also
    ----------
    :func:`profile_callable`
        Further details on function signature.
    '''

    # Defer BETSE-specific heavyweight imports.
    from betse.lib import libs
    from betse.util.path import files

    # Log this fact.
    logs.log_debug('Line-granularity profiling enabled.')

    # Raise an exception unless the optional "pprofile" dependency is available.
    libs.die_unless_runtime_optional('pprofile')

    # Defer dependency-specific heavyweight imports.
    from pprofile import Profile

    # Line-granularity profile of the subsequent call to this callable.
    profile = Profile()

    # Value returned by calling this callable with these arguments, storing a
    # profile of this call into this "profile" object.
    return_value = profile.runcall(call, *args, **kwargs)

    #FIXME: Reenable support for logging this profile output *AFTER* we
    #implement support for reducing such output to only the slowest lines.
    #Currently, profiled timings for *ALL* lines in the codebase are output.
    #Which is ludicrous, as the codebase is approximately ~80,000 lines of code.
    #Reducing such output will require regular expression-based matching of
    #output resembling:
    #
    #     Command line: ['demo/threads.py']
    #     Total duration: 1.00573s
    #     File: demo/threads.py
    #     File duration: 1.00168s (99.60%)
    #     Line #|      Hits|         Time| Time per hit|      %|Source code
    #     ------+----------+-------------+-------------+-------+-----------
    #          1|         2|  3.21865e-05|  1.60933e-05|  0.00%|import threading
    #          2|         1|  5.96046e-06|  5.96046e-06|  0.00%|import time
    #          3|         0|            0|            0|  0.00%|
    #          4|         2|   1.5974e-05|  7.98702e-06|  0.00%|def func():
    #          5|         1|      1.00111|      1.00111| 99.54%|  time.sleep(1)
    #          6|         0|            0|            0|  0.00%|
    #          7|         2|  2.00272e-05|  1.00136e-05|  0.00%|def func2():
    #          8|         1|  1.69277e-05|  1.69277e-05|  0.00%|  pass
    #
    #To reduce this output (in order):
    #
    #1. Extract all lines prefixing the actual table rows into a separate local
    #   string variable -- say, "lines_preamble".
    #2. Sort all remaining lines via numeric contents of the fifth column, "%".
    #3. Drop all sorted lines except the first 48 or so, again.
    #4. Logging the concatenation of "lines_preamble" with the remaining lines.
    #FIXME: Consider contributing the result back to "pprofile".

    # If the caller requested this profile be logged...
    # if is_profile_logged:
    if False:
        # String buffer of all profiled lines.
        lines_annotated = StringIO()

        # Annotate all profiled lines into this string buffer. Unlike the
        # canonical "cProfile" and "profile" modules, this third-party module
        # simplistically provides no support for sorting or truncating the
        # resulting output.
        profile.annotate(out=lines_annotated)

    # If the caller requested this profile be serialized to a file...
    if profile_filename is not None:
        # Log this serialization.
        logs.log_info(
            'Writing Callgrind-formatted profile to "%s".', profile_filename)

        # Serialize this profile to this file.
        with files.write_chars(profile_filename) as profile_file:
            profile.callgrind(out=profile_file)
    #FIXME: Eliminate this branch after logging profiling metadata above.

    # Else, the caller requested this profile *NOT* be serialized to a file. In
    # this case, since no profile metadata was logged, log a non-fatal warning.
    else:
        logs.log_warning(
            'Line-granularity profiling ignored: '
            'no profiling filename provided.')

    # Return the value returned by this call.
    return return_value

# ....................{ GLOBALS ~ private                  }....................
# Technically, the same effect is also achievable via getattr() on the current
# module object. Doing so is complicated by artificial constraints Python
# imposes on doing so (e.g., obtaining the current module object is obscure) and
# the PEP 20 doctrine of "Explicit is better than implicit." We beg to disagree.
# Nonetheless, the explicit approach remains preferable in this edge-case.
_PROFILE_TYPE_TO_PROFILER = {
    ProfileType.CALL: _profile_callable_call,
    ProfileType.LINE: _profile_callable_line,
    ProfileType.NONE: _profile_callable_none,
}
'''
Dictionary mapping from each supported type of profiling to the module function
performing this type of profiling.

This private global is intended for use _only_ by the public
:func:`profile_callable` function.
'''

# ....................{ TIMERS                             }....................
@type_check
def time_callable(
    call: CallableTypes,
    args: SequenceTypes = None,
    kwargs: MappingType = None,
    repetitions: int = 7,
    iterations: int = 1000,
) -> float:
    '''
    Time the passed callable with the passed positional and keyword arguments
    (if any) called the passed number of repetitions of the passed number of
    iterations, returning the time in seconds consumed by the fastest call to
    this callable.

    This function _only_ returns the minimum timing of all observed timings,
    discarding the time consumed by all calls other than the fastest call to
    this callable. Why? Because the timing of the fastest call is the most
    statistically signifant timing. All error in timing is **positive,**
    typically due to overhead associated with low-level kernel operations (e.g.,
    I/O) and unrelated running processes. By definition, error in timing cannot
    be negative. As astutely noted by the Stackoverflow answer below:

        There's no way to get negative error because a computer can't ever
        compute faster than it can compute!

    Since all timing error is positive, the minimum timing is the timing that
    exhibits minimum error. For all intents and purposes, all other timings are
    effectively irrelevant.

    Parameters
    ----------
    call : CallableTypes
        Callable to be timed.
    args : optional[SequenceTypes]
        Sequence of positional arguments to pass to each call to this callable.
        Defaults to `None`, in which no such arguments are passed.
    kwargs: optional[MappingType]
        Dictionary of keyword arguments to pass to each call to this callable.
        Defaults to `None`, in which no such arguments are passed.
    repetitions : optional[int]
        Number of times to repeat each number of times to call this callable.
        Defaults to a reasonably small value.
    iterations: optional[int]
        Number of times to call this callable for each repetition. The total
        number of calls is thus given by `repetitions * iterations`. Defaults to
        a reasonably large value.

    See Also
    ----------
    https://stackoverflow.com/a/24105845/2809027
        Stackoverflow answer strongly inspiring this implementation.
    '''

    # Partial function binding this callable to these arguments. Avoid
    # defaulting unpassed positional and keyword arguments to empty data
    # structures, as doing so appears to substantially skew timings and hence
    # should be avoided if feasible.
    #
    # If both positional and keyword arguments were passed, bind this callable
    # to both.
    callable_bound = None
    if args and kwargs:
        callable_bound = partial(call, *args, **kwargs)
    # Else if only positional arguments were passed, bind this callable to only
    # positional arguments.
    elif args:
        callable_bound = partial(call, *args)
    # Else if only keyword arguments were passed, bind this callable to only
    # keyword arguments.
    elif kwargs:
        callable_bound = partial(call, **kwargs)
    # Else, call this callable as is.
    else:
        callable_bound = call

    # Return the minimum timing of this callable repeated this number of times.
    return min(Timer(callable_bound).repeat(repetitions, iterations))
