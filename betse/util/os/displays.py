#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
High-level operating system (OS)-specific display facilities.
'''

#FIXME: Submit a Stackoverflow answer encapsulating this logic. The
#osx.is_aqua() function in particular would be useful to a wide audience.

# ....................{ IMPORTS                            }....................
from betse.util.type.callables import callable_cached
from collections import OrderedDict

# ....................{ TESTERS                            }....................
# For efficiency, cache the returned boolean for the duration of this process.
@callable_cached
def is_headfull() -> bool:
    '''
    `True` only if the active Python interpreter is running **headfull** (i.e.,
    with access to a GUI display, the common case when running under a
    conventional desktop, laptop, or tablet device).
    '''

    # Avoid circular import dependencies.
    from betse.util.os import oses
    from betse.util.os.brand import macos
    from betse.util.os.shell import envs

    # The current process is headfull if and only if...
    return (
        # This is Windows, the current process is *ALMOST* certainly headfull.
        # While certain server-specific variants of Windows can and often are
        # run headless (e.g., Windows Nano Server), there appears to be no known
        # means of reliably distinguishing a headless from headfull Windows
        # environment in pure Python. For simplicity, the latter is assumed.
        oses.is_windows() or

        # Else, this is a POSIX-compatible platform.
        #
        # Since all POSIX-compatible platforms of interest support the headfull
        # X11 display server, we efficiently test for the accessibility of this
        # server via the ${DISPLAY} environment variable inherited from the
        # parent shell environment first.
        envs.is_var('DISPLAY') or

        # Else, all possible alternative display servers specific to the current
        # platform *MUST* be iteratively tested for.
        #
        # If this is Linux, the only remaining display servers are:
        #
        # * Mir, accessible via the ${MIR_SOCKET} environment variable.
        # * Wayland, accessible via the ${WAYLAND_DISPLAY} environment variable.
        #
        # Ergo, the current process is headfull if and only if one of these
        # variables is inherited from the parent shell environment.
        (oses.is_linux() and envs.is_var('MIR_SOCKET', 'WAYLAND_DISPLAY',)) or

        # If this is OS X, the only remaining display server is Aqua.
        (oses.is_macos() and macos.is_aqua())

        # Else, this platform is unrecognized. For safety, this platform is
        # assumed to be headless.
    )


def is_headless() -> bool:
    '''
    `True` only if the active Python interpreter is running **headless** (i.e.,
    with _no_ access to a GUI display, often due to running remotely over an
    SSH-encrypted connection supporting only CLI input and output).
    '''

    return not is_headfull()    # Makes sense.

# ....................{ GETTERS ~ metadata                 }....................
def get_metadata() -> OrderedDict:
    '''
    Ordered dictionary synopsizing the current display.
    '''

    # Return this metadata.
    return OrderedDict((
        ('headless', is_headless()),
    ))
