#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
High-level **simulation phase cache** (e.g., container persisting previously
constructed large-scale objects for a simulation phase) functionality.
'''

# ....................{ IMPORTS                            }....................
from abc import ABCMeta  #, abstractmethod
from betse.science.simulate.simphase import SimPhase
from betse.util.py import references
from betse.util.type.types import type_check

# ....................{ CLASSES                            }....................
class SimPhaseCaches(object):
    '''
    Namespace containing all simulation phase-specific caches, each persisting
    previously constructed large-scale objects for subsequent reuse by a single
    simulation phase.

    Attributes
    ----------
    upscaled : SimPhaseCacheCellsUpscaled
        Subcache of all upscaled objects constructed for this phase.
    vector : SimPhaseCacheVector
        Subcache of all vectors constructed for this phase.
    vector_field : SimPhaseCacheVectorField
        Subcache of all vector fields constructed for this phase.
    '''

    # ..................{ INITIALIZORS                       }..................
    @type_check
    def __init__(self, phase: SimPhase) -> None:
        '''
        Initialize this simulation phase cache.

        Parameters
        ----------
        phase : SimPhase
            Parent simulation phase.
        '''

        # Avoid circular import dependencies.
        from betse.science.simulate.cache.cacheupscaled import (
            SimPhaseCacheUpscaled)
        from betse.science.simulate.cache.cachevec import SimPhaseCacheVector
        from betse.science.simulate.cache.cachevecfld import (
            SimPhaseCacheVectorField)

        # Classify all subcaches imported above.
        self.upscaled = SimPhaseCacheUpscaled(phase)
        self.vector = SimPhaseCacheVector(phase)
        self.vector_field = SimPhaseCacheVectorField(phase)

# ....................{ SUPERCLASSES                       }....................
class SimPhaseCacheABC(object, metaclass=ABCMeta):
    '''
    Abstract base class of all **simulation phase subcache** (i.e., container
    persisting previously constructed large-scale objects for some facet of a
    simulation phase) subclasses.

    Design
    ----------
    Subcaches provide namespace isolation but are otherwise purely superficial.
    Technically, all objects cached by a subcache could simply be cached by the
    parent :class:`SimPhaseCaches` object instead. Doing so would quickly become
    cumbersome, however, both for maintenance and reuse.

    Attributes
    ----------
    _phase : SimPhase
        Parent simulation phase. This attribute is technically accessible as
        :attr:`_cache.phase` but is provided by this class for convenience.
    '''

    # ..................{ INITIALIZORS                       }..................
    @type_check
    def __init__(self, phase: SimPhase) -> None:
        '''
        Initialize this simulation phase subcache.

        Parameters
        ----------
        phase : SimPhase
            Parent simulation phase.
        '''

        # Classify all passed parameters as weak rather than strong reference,
        # circumventing circular references and complications thereof.
        self._phase = references.proxy_weak(phase)