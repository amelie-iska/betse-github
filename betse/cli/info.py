#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
`info` subcommand for `betse`'s command line interface (CLI).
'''

#FIXME; For aesthetics, convert to yppy-style "cli.memory_table" output.

# ....................{ IMPORTS                            }....................
from collections import OrderedDict
from betse import metadata, pathtree
from betse.lib import libs
from betse.lib.matplotlib.matplotlibs import mpl_config
from betse.util.io import logs
from betse.util.py import pys
from betse.util.os import oses, processes
from io import StringIO

# ..................{ SUBCOMMANDS ~ info                     }..................
#FIXME: This function should probably accept new parameters describing current
#logging state.

def output_info() -> None:
    '''
    Print all output for the `info` subcommand.
    '''

    logs.log_info(
        'Harvesting system information. (This may take a moment.)')

    # Dictionary of human-readable labels to dictionaries of all
    # human-readable keys and values categorized by such labels. All such
    # dictionaries are ordered so as to preserve order in output.
    info_type_to_dict = OrderedDict((
        # Application metadata.
        (metadata.NAME.lower(), OrderedDict((
            ('basename', processes.get_current_basename()),
            ('version', metadata.__version__),
            ('authors', metadata.AUTHORS),
            ('home directory', pathtree.HOME_DIRNAME),
            ('dot directory',  pathtree.DOT_DIRNAME),
            ('data directory', pathtree.DATA_DIRNAME),
            ('default config file', pathtree.CONFIG_DEFAULT_FILENAME),
            ('default config geometry directory', pathtree.DATA_GEOMETRY_DIRNAME),

            #FIXME: Incorrect now! This is configurable at runtime.
            ('log file', pathtree.LOG_DEFAULT_FILENAME),
        ))),

        # Dependencies metadata.
        ('dependencies', libs.get_metadata()),

        # "matplotlib" metadata.
        ('matplotlib', mpl_config.get_metadata()),

        # Python metadata.
        ('python', pys.get_metadata()),

        # Operating system (OS) metadata.
        ('os', oses.get_metadata()),
    ))

    # String buffer formatting such information.
    info_buffer = StringIO()

    # True if this is the first label to be output.
    is_info_type_first = True

    # Format each such dictionary under its categorizing label.
    for info_type, info_dict in info_type_to_dict.items():
        # If this is *NOT* the first label, delimit this label from the
        # prior label.
        if is_info_type_first:
            is_info_type_first = False
        else:
            info_buffer.write('\n')

        # Format such label.
        info_buffer.write('{}:\n'.format(info_type))

        # Format such dictionary.
        for info_key, info_value in info_dict.items():
            info_buffer.write('  {}: {}\n'.format(info_key, info_value))

    # Log rather than merely output such string, as logging simplifies
    # cliest-side bug reporting.
    logs.log_info(info_buffer.getvalue())

# --------------------( WASTELANDS                         )--------------------
    # info_buffer.write('\n')
#FUXME: Also print the versions of installed mandatory dependencies.
