#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Unit tests for the `@type_check` decorator, implementing a rudimentary subset of
PEP 484-style type checking based on Python 3.x function annotations.
'''

# ....................{ IMPORTS                            }....................
import pytest

# ....................{ TESTS                              }....................
def test_type_check_noop() -> None:
    '''
    Test type checking for a function with no function annotations, reducing to
    _no_ type checking.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Unannotated function to be type checked.
    @type_check
    def khorne(gork, mork):
        return gork + mork

    # Call this function and assert the expected return value.
    assert khorne('WAAAGH!', '!HGAAAW') == 'WAAAGH!!HGAAAW'

# ....................{ TESTS ~ pass : param               }....................
def test_type_check_pass_param_keyword_and_positional() -> None:
    '''
    Test type checking for a function call successfully passed both annotated
    positional and keyword parameters.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Function to be type checked.
    @type_check
    def slaanesh(daemonette: str, keeper_of_secrets: str) -> str:
        return daemonette + keeper_of_secrets

    # Call this function with both positional and keyword arguments and assert
    # the expected return value.
    assert slaanesh(
        'Seeker of Decadence', keeper_of_secrets="N'Kari") == (
        "Seeker of DecadenceN'Kari")


def test_type_check_pass_param_keyword_only() -> None:
    '''
    Test type checking for a function call successfully passed an annotated
    keyword-only parameter following an `*` or `*args` parameter.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Function to be type checked.
    @type_check
    def changer_of_ways(sky_shark: str, *, chaos_spawn: str) -> str:
        return sky_shark + chaos_spawn

    # Call this function with keyword arguments and assert the expected return
    # value.
    assert changer_of_ways(
        'Screamers', chaos_spawn="Mith'an'driarkh") == (
        "ScreamersMith'an'driarkh")


def test_type_check_pass_param_tuple() -> None:
    '''
    Test type checking for a function call successfully passed a parameter
    annotated as a tuple.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Function to be type checked.
    @type_check
    def genestealer(tyranid: str, hive_fleet: (str, int)) -> str:
        return tyranid + str(hive_fleet)

    # Call this function with each of the two types listed in the above tuple.
    assert genestealer('Norn-Queen', 'Behemoth') == 'Norn-QueenBehemoth'
    assert genestealer('Carnifex', 0xDEADBEEF) == 'Carnifex3735928559'


def test_type_check_pass_param_custom() -> None:
    '''
    Test type checking for a function call successfully passed a parameter
    annotated as a user-defined rather than builtin type.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # User-defined type.
    class CustomTestStr(str):
        pass

    # Function to be type checked.
    @type_check
    def hrud(gugann: str, delphic_plague: CustomTestStr) -> str:
        return gugann + delphic_plague

    # Call this function with each of the two types listed in the above tuple.
    assert hrud(
        'Troglydium hruddi', delphic_plague=CustomTestStr('Delphic Sink')) == (
        'Troglydium hruddiDelphic Sink')

# ....................{ TESTS ~ pass : return              }....................
def test_type_check_pass_return_none() -> None:
    '''
    Test type checking for a function call successfully returning `None` and
    annotated as such.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Function to be type checked.
    @type_check
    def xenos(interex: str, diasporex: str) -> None:
        interex + diasporex

    # Call this function and assert no value to be returned.
    assert xenos(
        'Luna Wolves', diasporex='Iron Hands Legion') is None

# ....................{ TESTS ~ fail                       }....................
def test_type_check_fail_keyword_unknown() -> None:
    '''
    Test type checking for an annotated function call passed an unrecognized
    keyword parameter.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Annotated function to be type checked.
    @type_check
    def tau(kroot: str, vespid: str) -> str:
        return kroot + vespid

    # Call this function with an unrecognized keyword parameter and assert the
    # expected exception.
    with pytest.raises(TypeError) as exception:
        tau(kroot='Greater Good', nicassar='Dhow')

    # For readability, this should be a "TypeError" synopsizing the exact issue
    # raised by the Python interpreter on calling the original function rather
    # than a "TypeError" failing to synopsize the exact issue raised by the
    # wrapper type-checking the original function. Since the function
    # annotations defined above guarantee that the exception message of the
    # latter will be suffixed by "not a str", ensure this is *NOT* the case.
    assert not str(exception.value).endswith('not a str')


def test_type_check_fail_param_name() -> None:
    '''
    Test type checking for a function accepting a parameter name reserved for
    use by the `@type_check` decorator.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Define a function accepting a reserved parameter name and assert the
    # expected exception.
    with pytest.raises(NameError):
        @type_check
        def jokaero(weaponsmith: str, __beartype_func: str) -> str:
            return weaponsmith + __beartype_func

# ....................{ TESTS ~ fail : type                }....................
def test_type_check_fail_param_type() -> None:
    '''
    Test type checking for an annotated function call failing a parameter type
    check.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Annotated function to be type checked.
    @type_check
    def eldar(isha: str, asuryan: (str, int)) -> str:
        return isha + asuryan

    # Call this function with an invalid type and assert the expected exception.
    with pytest.raises(TypeError):
        eldar('Mother of the Eldar', 100.100)


def test_type_check_fail_return_type() -> None:
    '''
    Test type checking for an annotated function call failing a return type
    check.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Annotated function to be type checked.
    @type_check
    def necron(star_god: str, old_one: str) -> str:
        return 60e6

    # Call this function and assert the expected exception.
    with pytest.raises(TypeError):
        necron("C'tan", 'Elder Thing')

# ....................{ TESTS ~ fail : annotation          }....................
def test_type_check_fail_annotation_param() -> None:
    '''
    Test type checking for a function with an unsupported parameter annotation.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Assert the expected exception from attempting to type check a function
    # with a parameter annotation that is *NOT* a type.
    with pytest.raises(TypeError):
        @type_check
        def nurgle(nurgling: str, great_unclean_one: 'Bringer of Poxes') -> str:
            return nurgling + great_unclean_one


def test_type_check_fail_annotation_return() -> None:
    '''
    Test type checking for a function with an unsupported return annotation.
    '''

    # Import this decorator.
    from betse.util.type.types import type_check

    # Assert the expected exception from attempting to type check a function
    # with a return annotation that is *NOT* a type.
    with pytest.raises(TypeError):
        @type_check
        def tzeentch(disc: str, lord_of_change: str) -> 'Player of Games':
            return disc + lord_of_change
