#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2018 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
High-level **simulation export pipeline** (i.e., container of related, albeit
isolated, simulation export actions to be run iteratively) functionality.
'''

# ....................{ IMPORTS                           }....................
from betse.science.pipe.pipeabc import SimPipeABC

# ....................{ SUPERCLASSES                      }....................
class SimPipeExportABC(SimPipeABC):
    '''
    Abstract base class of all **simulation export pipelines** (i.e.,
    subclasses iteritavely exporting all variations on a single type of
    simulation export, either in parallel *or* in series).
    '''

    # ..................{ SUPERCLASS                        }..................
    @property
    def _runner_method_name_prefix(self) -> str:
        return  'export_'


    @property
    def _verb_continuous(self) -> str:
        return 'Exporting'