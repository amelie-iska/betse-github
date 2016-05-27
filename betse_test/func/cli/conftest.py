#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Global functional test configuration for BETSE's command-line interface (CLI).

`py.test` implicitly imports all functionality defined by this module into all
CLI-specific functional test modules. As this functionality includes all
publicly declared functional fixtures in this `fixture` subpackage, these tests
may reference these fixtures without explicit imports.
'''

# ....................{ IMPORTS ~ fixture                  }....................
from betse_test.func.cli.fixture.command import betse_cli