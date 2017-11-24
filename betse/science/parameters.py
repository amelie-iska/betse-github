#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

# ....................{ IMPORTS                            }....................
import numpy as np
from betse import pathtree
from betse.exceptions import BetseSimConfigException, BetseSimPhaseException
from betse.lib.matplotlib import mplcolormap
from betse.lib.yaml.yamlalias import yaml_alias, yaml_enum_alias
from betse.lib.yaml.abc.yamlabc import YamlFileABC
from betse.science.config.confenum import (
    CellLatticeType, IonProfileType)
from betse.science.tissue.event import tisevevolt
from betse.science.simulate.simphase import SimPhaseKind
from betse.science.tissue.picker.tispickimage import TissuePickerImage
# from betse.util.io.log import logs
from betse.util.path import dirs, pathnames
# from betse.util.type.call.memoizers import property_cached
from betse.util.type.types import type_check, IterableTypes, SequenceTypes

# ....................{ CLASSES                            }....................
#FIXME: Rename the "I_overlay" attribute to "is_plot_current_overlay".
class Parameters(YamlFileABC):
    '''
    High-level simulation configuration encapsulating the low-level dictionary
    deserialized (i.e., parsed) from the user-defined YAML-formatted file
    underlying the current simulation.

    Attributes (Path: Export)
    ----------
    init_export_dirname : str
        Absolute pathname of the directory containing results exported from this
        simulation's most recent initialization run, guaranteed to exist.
    init_export_dirname_relative : str
        Relative pathname of the directory containing results exported from this
        simulation's most recent initialization run, relative to the absolute
        path of the directory containing this simulation configuration's YAML
        file.
    sim_export_dirname : str
        Absolute pathname of the directory containing results exported from this
        simulation's most recent simulation run, guaranteed to exist.
    sim_export_dirname_relative : str
        Relative pathname of the directory containing results exported from this
        simulation's most recent simulation run, relative to the absolute path
        of the directory containing this simulation configuration's YAML file.

    Attributes (Path: Pickle: Seed)
    ----------
    seed_pickle_basename : str
        Basename of the pickled file providing this simulation's most recently
        seeded cell cluster within the current :attr:`init_dirname`.
    init_pickle_basename : str
        Basename of the pickled file providing this simulation's most recent
        initialization run within the current :attr:`init_dirname`.
    init_pickle_dirname : str
        Absolute pathname of the directory containing this simulation's most
        recently seeded cell cluster *and* initialization run, guaranteed to
        exist.
    init_pickle_dirname_relative : str
        Relative pathname of the directory containing this simulation's most
        recently seeded cell cluster *and* initialization run, relative to the
        absolute path of the directory containing this simulation
        configuration's YAML file.
    sim_pickle_basename : str
        Basename of the pickled file providing this simulation's most recent
        simulation run within the current :attr:`sim_dirname`.
    sim_pickle_dirname : str
        Absolute pathname of the directory containing this simulation's most
        recent simulation run, guaranteed to exist.
    sim_pickle_dirname_relative : str
        Relative pathname of the directory this simulation's most
        recent simulation run, relative to the absolute path of the directory
        containing this simulation configuration's YAML file.

    Attributes (Space: Cell)
    ----------
    cell_radius : float
        Radius in meters of each cell in this cluster. This should typically be
        within an order of magnitude of the recommended default of ``5.0e-6``.

    Attributes (Space: Cell Cluster)
    ----------
    cell_lattice_disorder : float
        Degree to which cell boundaries spatially deviate from the base cell
        lattice. If 0.0, cells rigidly conform to this lattice; else, cells
        randomly deviate from this lattice. Increasing this increases the
        entropy (i.e., randomness) of these deviations, producing an
        increasingly chaotic arrangement of cells. This should typically reside
        in the range ``[0.0, 0.8]``.
    cell_lattice_type : CellLatticeType
        Type of **base cell lattice** (i.e., uniform grid to which cells are
        situated *before* random lattice disorder is applied).

    Attributes (Space: Environment)
    ----------
    grid_size : int
        Number of square grid spaces (in both the X and Y dimensions) to
        computationally divide this simulation's square environment into.
        Increasing this increases simulation granularity and hence stability at
        a quadratic increase in space and time costs (i.e., ``O(grid_size **
        2)``). This should typically reside in the range ``[10, 60]``.
    is_ecm : bool
        ``True`` only if the extracellular matrix (ECM) simulating
        **extracellular spaces** (i.e., the environment surrounding each cell in
        the cluster) is enabled. Disabling this reduces simulation accuracy at a
        substantial reduction in space and time costs.
    world_len : float
        Length in meters of both the X and Y dimensions of this simulation's
        square environment. This should typically reside in the range ``[80e-6,
        1000e-6]``.

    Attributes (Time: Total)
    ----------
    init_time_total : float
        Duration in seconds of the initialization phase *not* modified by
        extraneous settings (e.g., gap junction acceleration factor).
    sim_time_total : float
        Duration in seconds of the simulation phase *not* modified by extraneous
        settings (e.g., gap junction acceleration factor).
    total_time : float
        Duration in seconds of the current simulation phase *not* modified by
        extraneous settings (e.g., gap junction acceleration factor).
    total_time_accelerated : float
        Duration in seconds of the current simulation phase accelerated by the
        gap junction acceleration factor.

    Attributes (Time: Step)
    ----------
    init_time_step : float
        Duration in seconds of each time step (including sampled and unsampled)
        for the initialization phase.
    sim_time_step : float
        Duration in seconds of each time step (including sampled and unsampled)
        for the initialization phase.
    dt : float
        Duration in seconds of each time step (including sampled and unsampled)
        for the current simulation phase.

    Attributes (Time: Sampling)
    ----------
    init_time_sampling : float
        Duration in seconds between each sampled time step (including that
        sampled time step itself) for the initialization phase. Decreasing this
        duration increases the number of time steps for which data is exported
        from this phase at a linear cost in space consumption.
    sim_time_sampling : float
        Duration in seconds between each sampled time step (including that
        sampled time step itself) for the simulation phase. Decreasing this
        duration increases the number of time steps for which data is exported
        from this phase at a linear cost in space consumption.
    t_resample : float
        Number of time steps between each sampled time step, including that
        sampled time step itself. Notably, if the current time step ``t`` is a
        sampled time step:
        * ``t + t_resample`` is the next sampled time step (if any).
        * ``t - t_resample`` is the prior sampled time step (if any).

    Attributes (Ion)
    ----------
    ion_profile : IonProfileType
        Type of **ion profile** (i.e., predefined set of all extracellular and
        cytosolic ions enabled by this simulation).
    ions_dict : dict
        Dictionary mapping:
        * From each of the following names of a supported core ion:
          * ``Na``, the sodium cation Na+.
          * ``K``, the potassium cation K+.
          * ``Ca``, the calcium cation Ca2+.
          * ``Cl``, the chloride anion Cl-.
          * ``H``, the hydrogen cation H+.
          * ``M``, the M anion bicarbonate HCO3-.
          * ``P``, the anionic protein P-.
        * To either:
          * 0, if that ion is disabled by the ion profile in the current
            simulation configuration.
          * 1, if that ion is enabled by that ion profile.

    Attributes (Ion: Initial)
    ----------
    conc_env_ca : float
        Initial extracellular concentration of the Ca2+ (calcium) cation.
    conc_env_cl : float
        Initial extracellular concentration of the Cl- (chloride) anion.
    conc_env_k : float
        Initial extracellular concentration of the K+ (potassium) cation.
    conc_env_m : float
        Initial extracellular concentration of the M- (unidentified) anion,
        synthetically manufactured to enforce charge-balancing over all
        environmental spaces for both simulation stability and correctness.
    conc_env_na : float
        Initial extracellular concentration of the Na+ (sodium) cation.
    conc_env_p : float
        Initial extracellular concentration of the P- (protein) anion.

    Attributes (Ion: Initial: Custom)
    ----------

    Attributes (Tissue)
    ----------
    is_tissue_profiles : bool
        ``True`` only if **tissue profiles** (i.e., user-defined regions within
        the cluster to which specific base membrane diffusion profiles,
        interventions, and individualized dynamics can be applied) are enabled.
        Note that tissue profiles should typically *always* be enabled.

    Attributes (General: Scalars)
    ----------
    cell_polarizability : NumericTypes
        Constant defining the rate of cell polarizability change in electric
        fields, typically ranging ``[0.0, 1.0e-3]``.

    Attributes (Exports)
    ----------
    anim : SimConfAnimAll
        Subconfiguration encapsulating exported simulation animations.
    plot : SimConfPlotAll
        Subconfiguration encapsulating exported simulation plots.
    plot_cell : int
        0-based index of the cell to isolate all single-cell time plots to.
        Defaults to 0, the index assigned to the first cell guaranteed to exist.
        Note that cell indices are seed-specific and may be visualized via the
        :attr:`enumerate_cells` boolean.
    I_overlay : bool
        ``True`` only if overlaying either electric current or concentration
        flux streamlines on appropriate plots and animations.

    Attributes (Tissue)
    ----------
    clipping_bitmap_matcher : TissuePickerImage
        Object encapsulating the bitmap whose colored pixel area specifies the
        global geometry mask to which all tissue profile bitmaps will be
        clipped.
    closed_bound : bool
        `True` if environmental boundaries are closed (i.e., _not_ open).
    tissue_profiles : list
        List of ordered dictionaries, each describing a **tissue profile**
        (i.e., instance of the :class:`ProfileABC` class identifying cells
        to be associated with particular simulation constants and parameters).
    '''

    # ..................{ ALIASES                            }..................
    # To sanitize computation throughout the codebase, *ALL* real numbers are
    # required to be floating point rather the more general "NumericTypes" type
    # (i.e., either floating point or integer). Due to magic internal to the
    # yaml_alias() data descriptor, integer values are both silently and safely
    # cast to floating point values.

    # ..................{ ALIASES ~ export : dir             }..................
    init_export_dirname_relative = yaml_alias(
        "['results file saving']['init directory']", str)
    sim_export_dirname_relative  = yaml_alias(
        "['results file saving']['sim directory']", str)

    # ..................{ ALIASES ~ pickle : dir             }..................
    init_pickle_dirname_relative = yaml_alias(
        "['init file saving']['directory']", str)
    sim_pickle_dirname_relative = yaml_alias(
        "['sim file saving']['directory']", str)

    # ..................{ ALIASES ~ pickle : base            }..................
    seed_pickle_basename = yaml_alias("['init file saving']['worldfile']", str)
    init_pickle_basename = yaml_alias("['init file saving']['file']", str)
    sim_pickle_basename  = yaml_alias("['sim file saving']['file']", str)

    # ..................{ ALIASES ~ space : cell             }..................
    cell_radius = yaml_alias("['world options']['cell radius']", float)

    # ..................{ ALIASES ~ space : cell cluster     }..................
    cell_lattice_disorder = yaml_alias(
        "['world options']['lattice disorder']", float)
    cell_lattice_type = yaml_enum_alias(
        "['world options']['lattice type']", CellLatticeType)

    # ..................{ ALIASES ~ space : env              }..................
    grid_size = yaml_alias("['general options']['comp grid size']", int)
    is_ecm = yaml_alias(
        "['general options']['simulate extracellular spaces']", bool)
    world_len = yaml_alias("['world options']['world size']", float)

    # ..................{ ALIASES ~ time : total             }..................
    init_time_total = yaml_alias("['init time settings']['total time']", float)
    sim_time_total  = yaml_alias("['sim time settings']['total time']", float)

    # ..................{ ALIASES ~ time : step              }..................
    init_time_step = yaml_alias("['init time settings']['time step']", float)
    sim_time_step  = yaml_alias("['sim time settings']['time step']", float)

    # ..................{ ALIASES ~ time : sampling          }..................
    init_time_sampling = yaml_alias(
        "['init time settings']['sampling rate']", float)
    sim_time_sampling = yaml_alias(
        "['sim time settings']['sampling rate']", float)

    # ..................{ ALIASES ~ ion                      }..................
    #FIXME: Consider shifting all ion-centric functionality into a dedicated
    #"ion" instance variable, instantiated to be an instance of a newly defined
    #"SimConfIonProfile" class. Ion handling currently appears to consume in
    #upwards of a third of this entire submodule.
    ion_profile = yaml_enum_alias(
        "['general options']['ion profile']", IonProfileType)

    # ..................{ ALIASES ~ ion ~ custom             }..................
    #FIXME: Actually use below.
    ion_profile_custom_conc_env_na = yaml_alias(
        "['general options']['customized ion profile']"
        "['extracellular Na+ concentration']", float)

    # ..................{ ALIASES ~ tissue                   }..................
    #FIXME: Does this boolean actually serve a demonstrable purpose? I might be
    #offbase here, but don't we always want tissue profiles? Is there actually a
    #valid use case for even disabling all tissue profiles?
    is_tissue_profiles = yaml_alias(
        "['tissue profile definition']['profiles enabled']", bool)

    # ..................{ ALIASES ~ scalar                   }..................
    cell_polarizability = yaml_alias(
        "['internal parameters']['cell polarizability']", float)

    # ..................{ READERS                            }..................
    #FIXME: Convert all or most of the variables parsed by this method into
    #aliases of the above form. Brainy rainbows!
    @type_check
    def load(self, *args, **kwargs) -> None:

        # Avoid circular import dependencies.
        from betse.science.config import confcompat

        # Defer to the superclass implementation.
        super().load(*args, **kwargs)

        # Preserve backward compatibility with prior configuration formats
        # *BEFORE* other initialization, which expects the passed YAML file to
        # conform to the current configuration format.
        confcompat.upgrade_sim_conf(self)

        # Initialize paths specified by this configuration.
        self._init_paths()

        #---------------------------------------------------------------------------------------------------------------
        # GENERAL OPTIONS
        #---------------------------------------------------------------------------------------------------------------

        self.autoInit = self._conf['automatically run initialization']

        #FIXME: This attribute is largely vestigial and currently only
        #referenced in two other locations in the codebase. While still vital,
        #there exists no demonstrable reason to ever externally configure this.
        #Contemplate excising this configuration option from our YAML file and
        #instead hard-coding this option's default value (i.e., 50) within the
        #codebase itself as a global magic number.
        self.plot_grid_size = int(self._conf['general options']['plot grid size'])

        #---------------------------------------------------------------------------------------------------------------
        # WORLD OPTIONS
        #---------------------------------------------------------------------------------------------------------------

        # Geometric constants and factors
        self.wsx = self.world_len  # the x-dimension of the world space [m]
        self.wsy = self.world_len  # the y-dimension of the world space [m]
        self.cell_height = float(self._conf['world options']['cell height'])  # the height of a cell in the z-direction
        self.cell_space = float(self._conf['world options']['cell spacing'])  # the true cell-cell spacing

        volmult = float(self._conf['internal parameters']['environment volume multiplier'])

        self.vol_env = volmult*self.wsx*self.wsy*self.cell_height  # environmental volume for "no ECM" simulation

        #---------------------------------------------------------------------------------------------------------------
        # TISSUE PROFILES
        #---------------------------------------------------------------------------------------------------------------

        #FIXME: Excise this method after the above logic has been enabled.
        self._init_tissue_and_cut_profiles()

        #---------------------------------------------------------------------------------------------------------------
        # TARGETED INTERVENTIONS
        #---------------------------------------------------------------------------------------------------------------

        #FIXME: This dictionary appears to be superfluous. It's never iterated
        #over or treated like a dictionary. Its keys are only ever looked up. In
        #short, this dictionary shouldn't exist. For efficiency and sanity, all
        #keys of this dictionary should be refactored into simple instance
        #variables of this class (e.g., from "p.scheduled_options['Na_mem']" to
        #simply "p.event_Na_mem").
        #FIXME: After doing so, these instance variables should be refactored
        #from unreadable lists to objects with human-readable attribute names
        #(e.g., from "p.event_Na_mem[0]" to "p.event_Na_mem.start_time").
        #
        #The longest journey to the future begins tomorrow.

        # initialize dictionary keeping track of targeted scheduled options for the sim:
        self.scheduled_options = {}

        bool_Namem = bool(self._conf['change Na mem']['event happens'])
        bool_Kmem = bool(self._conf['change K mem']['event happens'])
        bool_Clmem = bool(self._conf['change Cl mem']['event happens'])
        bool_Camem = bool(self._conf['change Ca mem']['event happens'])
        bool_ecmj = bool(self._conf['break ecm junctions']['event happens'])
        bool_pressure = bool(self._conf['apply pressure']['event happens'])

        if bool_Namem is False:
            self.scheduled_options['Na_mem'] = 0
        elif bool_Namem is True:
            on_Namem = float(self._conf['change Na mem']['change start'])
            off_Namem = float(self._conf['change Na mem']['change finish'])
            rate_Namem = float(self._conf['change Na mem']['change rate'])
            multi_Namem = float(self._conf['change Na mem']['multiplier'])
            apply_Namem = self._conf['change Na mem']['apply to']
            function = self._conf['change Na mem']['modulator function']
            Namem = [on_Namem, off_Namem, rate_Namem, multi_Namem, apply_Namem,function]
            self.scheduled_options['Na_mem'] = Namem

        if bool_Kmem is False:
            self.scheduled_options['K_mem'] = 0
        elif bool_Kmem is True:
            on_Kmem = float(self._conf['change K mem']['change start'])
            off_Kmem = float(self._conf['change K mem']['change finish'])
            rate_Kmem = float(self._conf['change K mem']['change rate'])
            multi_Kmem = float(self._conf['change K mem']['multiplier'])
            apply_Kmem = self._conf['change K mem']['apply to']
            function = self._conf['change K mem']['modulator function']
            Kmem = [on_Kmem, off_Kmem, rate_Kmem, multi_Kmem, apply_Kmem,function]
            self.scheduled_options['K_mem'] = Kmem

        if bool_Clmem is False:
            self.scheduled_options['Cl_mem'] = 0
        elif bool_Clmem is True:
            on_Clmem = float(self._conf['change Cl mem']['change start'])
            off_Clmem = float(self._conf['change Cl mem']['change finish'])
            rate_Clmem = float(self._conf['change Cl mem']['change rate'])
            multi_Clmem = float(self._conf['change Cl mem']['multiplier'])
            apply_Clmem = self._conf['change Cl mem']['apply to']
            function = self._conf['change Cl mem']['modulator function']
            Clmem = [on_Clmem, off_Clmem, rate_Clmem, multi_Clmem, apply_Clmem, function]
            self.scheduled_options['Cl_mem'] = Clmem

        if bool_Camem is False:
            self.scheduled_options['Ca_mem'] = 0
        elif bool_Camem is True:
            on_Camem = float(self._conf['change Ca mem']['change start'])
            off_Camem = float(self._conf['change Ca mem']['change finish'])
            rate_Camem = float(self._conf['change Ca mem']['change rate'])
            multi_Camem = float(self._conf['change Ca mem']['multiplier'])
            apply_Camem = self._conf['change Ca mem']['apply to']
            function = self._conf['change Ca mem']['modulator function']
            Camem = [on_Camem, off_Camem, rate_Camem, multi_Camem, apply_Camem,function]
            self.scheduled_options['Ca_mem'] = Camem

        if bool_pressure:
            on_p = float(self._conf['apply pressure']['change start'])
            off_p = float(self._conf['apply pressure']['change finish'])
            rate_p = float(self._conf['apply pressure']['change rate'])
            multi_p = float(self._conf['apply pressure']['multiplier'])
            apply_p = self._conf['apply pressure']['apply to']
            function = self._conf['apply pressure']['modulator function']
            pressure_ops = [on_p, off_p, rate_p, multi_p, apply_p,function]

            self.scheduled_options['pressure'] = pressure_ops
        else:
            self.scheduled_options['pressure'] = 0

        #FIXME: Rename this dictionary key from "extV" to "external voltage".
        # Parameterize the voltage event if enabled.
        self.scheduled_options['extV'] = tisevevolt.make(p=self)

        if bool_ecmj is False:
            self.scheduled_options['ecmJ'] = 0
        elif bool_ecmj is True:
            on_ecmj = float(self._conf['break ecm junctions']['change start'])
            off_ecmj = float(self._conf['break ecm junctions']['change finish'])
            rate_ecmj = float(self._conf['break ecm junctions']['change rate'])
            apply_ecmj = self._conf['break ecm junctions']['apply to']
            mult_ecmj = 1.0 - float(self._conf['break ecm junctions'].get('multiplier', 0.0))
            ecmj = [on_ecmj, off_ecmj, rate_ecmj, apply_ecmj, mult_ecmj]

            self.scheduled_options['ecmJ'] = ecmj

        # Parameterize the cutting event if enabled.
        self.break_TJ = self._conf['cutting event'].get('break TJ', True)
        self.wound_TJ = float(self._conf['cutting event'].get('wound TJ', 0.1))
        wc = self._conf['cutting event']['wound channel']
        self.use_wound_channel = wc['use channel']
        self.wound_Dmax = float(wc['max conductivity'])
        self.wound_close_factor = float(wc['closure delay'])
        self.wound_channel_activators_list = wc.get('activators', None)
        self.wound_channel_activators_Km = wc.get('Km activators', None)
        self.wound_channel_activators_n = wc.get('n activators', None)
        self.wound_channel_inhibitors_list = wc.get('inhibitors', None)
        self.wound_channel_inhibitors_Km = wc.get('Km inhibitors', None)
        self.wound_channel_inhibitors_n = wc.get('n inhibitors', None)

        #---------------------------------------------------------------------------------------------------------------
        # GLOBAL INTERVENTIONS
        #---------------------------------------------------------------------------------------------------------------

        # initialize dictionary keeping track of global scheduled options for the sim:
        self.global_options = {}

        bool_Naenv = bool(self._conf['change Na env']['event happens'])
        bool_Kenv = bool(self._conf['change K env']['event happens'])
        bool_Clenv = bool(self._conf['change Cl env']['event happens'])
        bool_gjblock = bool(self._conf['block gap junctions']['event happens'])
        bool_temp =  bool(self._conf['change temperature']['event happens'])
        bool_NaKblock = bool(self._conf['block NaKATP pump']['event happens'])

        if bool_Kenv is False:
            self.global_options['K_env'] = 0
        elif bool_Kenv is True:
            on_Kenv = float(self._conf['change K env']['change start'])
            off_Kenv = float(self._conf['change K env']['change finish'])
            rate_Kenv = float(self._conf['change K env']['change rate'])
            multi_Kenv = float(self._conf['change K env']['multiplier'])
            kenv = [on_Kenv, off_Kenv, rate_Kenv, multi_Kenv]
            self.global_options['K_env'] = kenv

        if bool_Clenv is False:
            self.global_options['Cl_env'] = 0
        elif bool_Clenv is True:
            on_Clenv = float(self._conf['change Cl env']['change start'])
            off_Clenv = float(self._conf['change Cl env']['change finish'])
            rate_Clenv = float(self._conf['change Cl env']['change rate'])
            multi_Clenv = float(self._conf['change Cl env']['multiplier'])
            Clenv = [on_Clenv, off_Clenv, rate_Clenv, multi_Clenv]
            self.global_options['Cl_env'] = Clenv

        if bool_Naenv is False:
            self.global_options['Na_env'] = 0
        elif bool_Naenv is True:
            on_Naenv = float(self._conf['change Na env']['change start'])
            off_Naenv = float(self._conf['change Na env']['change finish'])
            rate_Naenv = float(self._conf['change Na env']['change rate'])
            multi_Naenv = float(self._conf['change Na env']['multiplier'])
            Naenv = [on_Naenv, off_Naenv, rate_Naenv, multi_Naenv]
            self.global_options['Na_env'] = Naenv

        if bool_gjblock is False:
            self.global_options['gj_block'] = 0
        elif bool_gjblock is True:
            on_gj = float(self._conf['block gap junctions']['change start'])
            off_gj = float(self._conf['block gap junctions']['change finish'])
            rate_gj = float(self._conf['block gap junctions']['change rate'])
            fraction_gj = float(self._conf['block gap junctions']['random fraction'])
            gjb = [on_gj,off_gj,rate_gj,fraction_gj]
            self.global_options['gj_block'] = gjb

        if bool_temp is False:
            self.global_options['T_change'] = 0
        elif bool_temp is True:
            on_T = float(self._conf['change temperature']['change start'])
            off_T = float(self._conf['change temperature']['change finish'])
            rate_T = float(self._conf['change temperature']['change rate'])
            multi_T = float(self._conf['change temperature']['multiplier'])
            temper = [on_T, off_T, rate_T, multi_T]
            self.global_options['T_change'] = temper

        if bool_NaKblock is False:
            self.global_options['NaKATP_block'] = 0
        elif bool_NaKblock is True:
            on_nak = float(self._conf['block NaKATP pump']['change start'])
            off_nak = float(self._conf['block NaKATP pump']['change finish'])
            rate_nak = float(self._conf['block NaKATP pump']['change rate'])
            nak = [on_nak,off_nak,rate_nak]
            self.global_options['NaKATP_block'] = nak


        #--------------------------------------------------------------------------------------------------------------
        # DYNAMIC CHANNELS
        #--------------------------------------------------------------------------------------------------------------

        # cells to effect with voltage gated channels: (choices = 'none','all','random1','random50', [1,2,3])
        # self.gated_targets = self._config['ion channel target cells']

        bool_cagK = bool(self._conf['calcium gated K+']['turn on'])
        bool_stretch = bool(self._conf['stretch gated Na+']['turn on'])

        # set specific character of gated ion channel dynamics:
        opNa = self._conf['voltage gated Na+']
        opNaP = self._conf['persistent vg Na+']
        opK = self._conf['voltage gated K+']
        opKir = self._conf['additional voltage gated K+']
        opFun = self._conf['funny current']
        opCa = self._conf['voltage gated Ca2+']
        # opcK = self._config['calcium gated K+']

        opStretch = self._conf['gated ion channel options']['stretch gated Na']

        self.flux_threshold = self._conf['gated ion channel options']['flux threshold']

        # voltage gated sodium:
        self.vgNa_bool = opNa['turn on']
        self.vgNa_type = opNa['channel type']
        self.vgNa_max = opNa['max value']
        self.vgNa_apply = opNa['apply to']

        # persistent voltage gated sodium:
        self.vgNaP_bool = opNaP['turn on']
        self.vgNaP_type = opNaP['channel type']
        self.vgNaP_max = opNaP['max value']
        self.vgNaP_apply = opNaP['apply to']

        # voltage gated potassium:
        self.vgK_bool = opK['turn on']
        self.vgK_type = opK['channel type']
        self.vgK_max = opK['max value']
        self.vgK_apply = opK['apply to']

        # inward rectifying voltage gated potassium:
        self.vgKir_bool = opKir['turn on']
        self.vgKir_type = opKir['channel type']
        self.vgKir_max = opKir['max value']
        self.vgKir_apply = opKir['apply to']

        # funny current voltage gated potassium:
        self.vgFun_bool = opFun['turn on']
        self.vgFun_type = opFun['channel type']
        self.vgFun_max = opFun['max value']
        self.vgFun_apply = opFun['apply to']

        # voltage gated Calcium:
        self.vgCa_bool = opCa['turn on']
        self.vgCa_type = opCa['channel type']
        self.vgCa_max = opCa['max value']
        self.vgCa_apply = opCa['apply to']


        # calcium gated K

        max_NaSt = float(self._conf['stretch gated Na+']['max value']) * 1.0e-9
        max_cagK = float(self._conf['calcium gated K+']['max value']) * 1.0e-9

        cagK = [max_cagK, 1.0e-3, 3.0]

        apply_cagK = self._conf['calcium gated K+']['apply to']

        cagK.append(apply_cagK)

        # stretch gated Na

        stNa = [max_NaSt,float(opStretch['hill K_half']),float(opStretch['hill n'])]

        apply_stNa = self._conf['stretch gated Na+']['apply to']

        stNa.append(apply_stNa)

        # initialize dictionary holding options for dynamic channels:
        self.vg_options = {}

        if bool_cagK is False:
            self.vg_options['K_cag'] = 0
        elif bool_cagK is True:
            self.vg_options['K_cag'] = cagK

        if bool_stretch is False:
            self.vg_options['Na_stretch'] = 0
        elif bool_stretch is True:
            self.vg_options['Na_stretch'] = stNa

        # Calcium TissueHandler: Calcium Induced Calcium Release (CICR).....................................................

        # include full calcium dynamics in the situation (i.e. endoplasmic reticulum, etc)?
        self.Ca_dyn = self._conf['Ca dynamics']['turn on']

        if self.Ca_dyn:
            self.serca_max = self._conf['Ca dynamics']['serca pump max'] # maximum rate of the ER membrane Ca++ ATPase (serca)
            self.max_er = self._conf['Ca dynamics']['max er']    # maximum conductivity of ER membrane Ca++ channel
            self.act_Km_Ca = self._conf['Ca dynamics']['act Km Ca'] # concentration at which calcium activates ER opening
            self.act_n_Ca = self._conf['Ca dynamics']['act n Ca']    # exponent for Ca activation
            self.inh_Km_Ca = self._conf['Ca dynamics']['inh Km Ca']  # concentration at which calcium inhibits ER opening
            self.inh_n_Ca = self._conf['Ca dynamics']['inh n Ca']     # exponent for Ca inhibition
            self.act_Km_IP3 = self._conf['Ca dynamics']['act Km IP3']   # concentration at which IP3 (if included in biomolecules) activates opening
            self.act_n_IP3 = self._conf['Ca dynamics']['act n IP3']     # exponent for IP3 (if included in biomolecules) activates opening

        #--------------------------------------------------------------------------------------------------------------
        #  CUSTOM GENERAL NETWORK (defined in main config file)
        #--------------------------------------------------------------------------------------------------------------

        self.network_config = self._conf.get('general network', None)

        if self.network_config is not None:
            self.molecules_enabled = self.network_config['implement network']
            self.mol_mit_enabled = self.network_config['enable mitochondria']

        else:
            self.mol_mit_enabled = False

        #---------------------------------------------------------------------------------------------------------------
        #  GENE REGULATORY NETWORKS
        #---------------------------------------------------------------------------------------------------------------

        self.grn_enabled = self._conf['gene regulatory network settings']['gene regulatory network simulated']

        self.grn_config_filename = self._conf['gene regulatory network settings']['gene regulatory network config']

        simgrndic = self._conf['gene regulatory network settings'].get('sim-grn settings', None)

        if simgrndic is not None:

            self.grn_piggyback = simgrndic['run network on']
            grn_savedir = simgrndic['save to directory']
            self.grn_savedir = pathnames.join(self.conf_dirname, grn_savedir)
            self.grn_savefile = simgrndic['save to file']

            self.grn_loadfrom = simgrndic['load from']

            if self.grn_loadfrom is not None and self.grn_loadfrom != 'None':
                self.loadMoG = pathnames.join(self.conf_dirname, self.grn_loadfrom)

            else:
                self.loadMoG = None

        else:

            self.grn_piggyback = 'seed'
            self.grn_savedir = pathnames.join(self.conf_dirname, 'GRN')
            self.grn_savefile = 'GRN_1.betse.gz'

            self.grn_loadfrom = None

            self.loadMoG = None

        # Define data paths for saving an initialization and simulation run:
        self.savedMoG = pathnames.join(self.grn_savedir, self.grn_savefile)

        #--------------------------------------------------------------------------------------------------------------
        # VARIABLE SETTINGS
        #--------------------------------------------------------------------------------------------------------------

        self.T = float(self._conf['variable settings']['temperature'])  # system temperature

        # electroosmotic fluid flow-----------------------------------------------------
        self.fluid_flow = self._conf['variable settings']['fluid flow']['include fluid flow']
        self.mu_water = float(self._conf['variable settings']['fluid flow']['water viscocity']) # visc water [Pa.s]

        # electrodiffusive movement pumps and channels -----------------------------------
        self.sim_eosmosis = self._conf['variable settings']['channel electroosmosis']['turn on']
        self.D_membrane = float(self._conf['variable settings']['channel electroosmosis']['membrane mobility'])
        self.z_channel = float(self._conf['variable settings']['channel electroosmosis']['channel charge'])
        self.z_pump = float(self._conf['variable settings']['channel electroosmosis']['pump charge'])

        # mechanical deformation ----------------------------------------------------------
        self.deformation = self._conf['variable settings']['deformation']['turn on']

        self.galvanotropism = float(self._conf['variable settings']['deformation']['galvanotropism'])
        self.td_deform = False # this has been disabled due to ongoing technical difficulties
        self.fixed_cluster_bound = self._conf['variable settings']['deformation']['fixed cluster boundary']
        self.youngMod = float(self._conf['variable settings']['deformation']['young modulus'])
        self.mu_tissue = float(self._conf['variable settings']['deformation']['viscous damping'])

        # osmotic and electrostatic pressures --------------------------------
        self.deform_osmo = self._conf['variable settings']['pressures']['include osmotic pressure']
        self.aquaporins = float(self._conf['variable settings']['pressures']['membrane water conductivity'])

        # calculate lame's parameters from young mod and the poisson ratio:
        self.poi = 0.49 # Poisson's ratio for the biological medium
        self.lame_mu = self.youngMod/(2*(1+self.poi))
        self.lame_lamb = (self.youngMod*self.poi)/((1+self.poi)*(1-2*self.poi))
        self.mu_membrane = 1.0 # membrane viscocity
        self.zeta = -70e-3  # zeta potential of cell membrane [V]

        # Gap junction parameters ------------------
        self.gj_surface = float(self._conf['variable settings']['gap junctions']['gap junction surface area'])
        self.gj_flux_sensitive = False
        self.gj_vthresh = float(self._conf['variable settings']['gap junctions']['gj voltage threshold'])
        self.gj_vgrad  = float(self._conf['variable settings']['gap junctions']['gj voltage window'])
        self.gj_min = float(self._conf['variable settings']['gap junctions']['gj minimum'])
        self.gj_respond_flow = False # (feature currently unsupported)
        self.v_sensitive_gj = self._conf['variable settings']['gap junctions']['voltage sensitive gj']

        # Microtubule properties........................................................................................

        mtb = self.config['variable settings'].get('microtubules', {})

        # if mtb is not None:

        self.use_microtubules = mtb.get('use microtubules', True)

        self.length_charge = float(mtb.get('charge per micrometer', -360.0))
        self.mt_radius = float(mtb.get('radius', 15.0e-9))
        self.mt_length = float(mtb.get('length', 5.0e-6))
        self.tubulin_dipole = float(mtb.get('tubulin unit dipole', 1750))
        self.tubulin_polar = float(mtb.get('tubulin polarizability', 50.0))

        self.tethered_tubule = (mtb.get('tethered tubule', True))

        self.cytoplasm_viscocity = 1.0e-2

        self.D_mtube = float(mtb.get('microtubule diffusion', 1.0))

        self.dilate_mtube_dt = float(mtb.get('time dilation factor', 1.0))

        self.init_mtx = mtb.get('microtubule initial x asymmetry', None)
        self.init_mty = mtb.get('microtubule initial y asymmetry', None)

        self.microtubules_orient_parallel = mtb.get('microtubules orient parallel', True)

        #...............................................................................................................

        # Environmental features and tight junctions ---------------------------------------------------
        self.env_type = True # for now, can't handle air boundaries
        self.cluster_open = True
        self.closed_bound = False
        self.D_tj = float(self._conf['variable settings']['tight junction scaling'])
        self.D_adh = float(self._conf['variable settings']['adherens junction scaling'])
        # tight junction relative ion movement properties:
        self.Dtj_rel = {}  # use a dictionary to hold the tj values:

        self.Dtj_rel['Na']=float(self._conf['variable settings']['tight junction relative diffusion']['Na'])
        self.Dtj_rel['K']=float(self._conf['variable settings']['tight junction relative diffusion']['K'])
        self.Dtj_rel['Cl']=float(self._conf['variable settings']['tight junction relative diffusion']['Cl'])
        self.Dtj_rel['Ca']=float(self._conf['variable settings']['tight junction relative diffusion']['Ca'])
        self.Dtj_rel['M']=float(self._conf['variable settings']['tight junction relative diffusion']['M'])
        self.Dtj_rel['P']=float(self._conf['variable settings']['tight junction relative diffusion']['P'])
        self.Dtj_rel['H']=float(self._conf['variable settings']['tight junction relative diffusion']['H'])

        #FIXME: Replace with use of an instantiated default tissue object. On
        #doing so, note that the calls to float() will reduce to noops and
        #should thus be removed.

        # default membrane diffusion constants: easy control of cell's base resting potential
        mem_concs_default = self._conf['tissue profile definition']['tissue'][
            'default']['diffusion constants']
        self.Dm_Na = float(mem_concs_default['Dm_Na'])     # sodium [m2/s]
        self.Dm_K  = float(mem_concs_default['Dm_K'])     #  potassium [m2/s]
        self.Dm_Cl = float(mem_concs_default['Dm_Cl'])    # chloride [m2/s]
        self.Dm_Ca = float(mem_concs_default['Dm_Ca'])   #  calcium [m2/s]
        self.Dm_H  = float(mem_concs_default['Dm_H'])    #  hydrogen [m2/s]
        self.Dm_M  = float(mem_concs_default['Dm_M'])    #  anchor ion [m2/s]
        self.Dm_P  = float(mem_concs_default['Dm_P'])     #  proteins [m2/s]

        # environmental (global) boundary concentrations:
        self.cbnd = self._conf['variable settings']['env boundary concentrations']

        # include noise in the simulation?
        self.channel_noise_level = float(self._conf['variable settings']['noise']['static noise level'])

        self.dynamic_noise = self._conf['variable settings']['noise']['dynamic noise']
        self.dynamic_noise_level = float(self._conf['variable settings']['noise']['dynamic noise level'])

        # Modulator functions ------------------------------------------------------------------------------------------
        self.gradient_x_properties = {}
        self.gradient_y_properties = {}
        self.gradient_r_properties = {}

        self.periodic_properties = {}
        self.f_scan_properties = {}

        self.gradient_x_properties['slope'] =float(self._conf['modulator function properties']['gradient_x']['slope'])
        self.gradient_x_properties['offset'] =float(self._conf['modulator function properties']['gradient_x']['offset'])
        self.gradient_x_properties['exponent'] = float(
                                        self._conf['modulator function properties']['gradient_x'].get('exponent', 1))

        self.gradient_y_properties['slope'] =float(self._conf['modulator function properties']['gradient_y']['slope'])
        self.gradient_y_properties['offset'] = float(self._conf['modulator function properties']['gradient_y']['offset'])
        self.gradient_y_properties['exponent'] = float(
                                    self._conf['modulator function properties']['gradient_y'].get('exponent', 1))

        self.gradient_r_properties['slope'] = float(self._conf['modulator function properties']['gradient_r']['slope'])
        self.gradient_r_properties['offset'] = float(self._conf['modulator function properties']['gradient_r']['offset'])
        self.gradient_r_properties['exponent'] = float(
            self._conf['modulator function properties']['gradient_r'].get('exponent', 1))

        self.periodic_properties['frequency'] = float(self._conf['modulator function properties']['periodic']['frequency'])
        self.periodic_properties['phase'] = float(self._conf['modulator function properties']['periodic']['phase'])

        self.f_scan_properties['f start'] = \
                                float(self._conf['modulator function properties']['f_sweep']['start frequency'])

        self.f_scan_properties['f stop'] = \
                                float(self._conf['modulator function properties']['f_sweep']['end frequency'])

        #initialize the f vect field to None as it's set depending on the sim timestep:

        self.f_scan_properties['f slope'] = None

        # filename to read for bitmap loading gradient definition:
        chk = self._conf['modulator function properties'].get('gradient_bitmap', None)

        if chk is not None:
            self.grad_bm_fn = self._conf['modulator function properties']['gradient_bitmap']['file']
            self.grad_bm_offset = self._conf['modulator function properties']['gradient_bitmap'].get('offset', 0.0)

        else:
            self.grad_bm_fn = None
            self.grad_bm_offset = None

        # ................{ EXPORTS                            }................
        ro = self._conf['results options']

        # Avoid circular import dependencies.
        from betse.science.config.export.confanim import SimConfAnimAll
        from betse.science.config.export.confplot import SimConfPlotAll

        # ................{ EXPORTS ~ anim                     }................
        # Animation subconfiguration.
        self.anim = SimConfAnimAll(conf=self._conf)

        # CSV subconfiguration.
        self.exportData = ro['save']['data']['all']['enabled']     # export all stored data for the plot_cell to a csv text file
        self.exportData2D = ro['save']['data']['vmem']['enabled']

        # use the GHK equation to calculate alt Vmem from params?
        self.GHK_calc = self._conf['variable settings']['use Goldman calculator']

        # ................{ EXPORTS ~ plot                     }................
        # Plot subconfiguration.
        self.plot = SimConfPlotAll(conf=self._conf)

        #FIXME: Replace all instances of "p.turn_all_plots_off" in the codebase
        #by "not p.plot.is_after_sim_show" and remove this attribute entirely.
        self.turn_all_plots_off = not self.plot.is_after_sim_show

        #FIXME: Replace all instances of "p.autosave" in the codebase
        #by "p.plot.is_after_sim_save" and remove this attribute entirely.
        self.autosave = self.plot.is_after_sim_save  # autosave all still images to a results directory

        self.plot_cutlines = ro['plot cutlines']

        # Colormaps.
        self.default_cm    = mplcolormap.get_colormap(ro['default colormap'])
        self.background_cm = mplcolormap.get_colormap(ro['background colormap'])

        # Colormap for plotting gj currents on top of default colormap.
        self.gj_cm = mplcolormap.get_colormap(ro['gj colormap'])

        # new options for plotting reaction network graphs:
        self.plot_network = ro['plot networks']
        self.network_cm = mplcolormap.get_colormap(ro['network colormap'])

        # Colors.
        self.vcolor = ro['vector and stream color']  # color of vector and streamlines

        # True if numbering cells in plots and animations.
        self.enumerate_cells = ro['enumerate cells']
        self.plot_cell = ro['plot cell index']             # State the cell index to use for single-cell time plots
        self.plot_networks_single_cell = ro['plot networks single cell']
        self.showCells = ro['show cells']     # True = polygon patch plots, False = trimesh
        self.I_overlay = ro['overlay currents']
        self.stream_density = ro['streamline density']
        self.IecmPlot = ro['plot total current']    # True = plot extracellular currents, false plot gj
        self.plotMask = ro['plot masked geometry']

        # Plot seed options.
        self.plot_cell_cluster = ro.get('plot cell cluster', True)
        self.plot_cell_connectivity = ro.get('plot cell connectivity diagram', True)
        self.plot_cluster_mask = ro.get('plot cluster mask', True)

        #--------------------------------------------------------------------------------------------------------------
        # INTERNAL USE ONLY
        #--------------------------------------------------------------------------------------------------------------

        iu = self._conf['internal parameters']

        self.interp_type = 'nearest'

        self.substances_affect_charge = iu['substances affect Vmem']  # Do Network substances function bioelectrically?

         # default free diffusion constants (cytoplasmic)
        self.Do_Na = float(iu['Do_Na'])      # free diffusion constant sodium [m2/s]
        self.Do_K = float(iu['Do_K'])      # free diffusion constant potassium [m2/s]
        self.Do_Cl = float(iu['Do_Cl'])     # free diffusion constant chloride [m2/s]
        self.Do_Ca = float(iu['Do_Ca'])     # free diffusion constant calcium [m2/s]
        self.Do_H = float(iu['Do_H'])      # free diffusion constant hydrogen [m2/s]
        self.Do_M = float(iu['Do_M'])     # free diffusion constant mystery anchor ion [m2/s]
        self.Do_P = float(iu['Do_P'])      # free diffusion constant protein [m2/s]

        # fixed levels of ATP, ADP and Pi, required for use in pump equations to get propper kinetics
        self.cATP = 1.5
        self.cADP = 0.1
        self.cPi = 0.1

        # pump parameters
        self.alpha_NaK = float(iu['alpha_NaK']) # maximum rate constant sodium-potassium ATPase per unit surface area

        # FIXME add these as options to the config
        self.KmNK_Na = 12.0   # NaKATPase enzyme ext Na half-max sat value (alpha1 = 12, alpha2 = 20, alpha3 = 60)
        self.KmNK_K = 0.2     # NaKATPase enzyme ext K half-max sat value (alpha1 = 0.2, alpha2 = 0.20, alpha3 = 0.09)
        self.KmNK_ATP = 0.5   # NaKATPase enzyme ATP half-max sat value

        self.alpha_Ca = float(iu['alpha_Ca']) # pump rate for calcium ATPase in membrane [1/mol*s] 2.0e-15

        # FIXME add these as options to the config:
        self.KmCa_Ca = 3.0e-3   # CaATPase enzyme Ca half-max sat value (1.7 - 2.8 for vascular, 0.25 for platlets)
        self.KmCa_ATP = 0.5    # CaATPase enzyme ATP half-max sat value

        # partial pressure dissolved CO2
        self.CO2 = 40.0   # [mmHg]
        self.cCO2 = 1.2

        # charge states of ions
        self.z_Na = 1
        self.z_K = 1
        self.z_Cl = -1
        self.z_Ca = 2
        self.z_H = 1
        self.z_P = -1
        self.z_M = -1

        # molar mass of ions (kg/mol):
        self.M_Na = 23e-3
        self.M_K = 39e-3
        self.M_Cl = 35e-3
        self.M_Ca = 40e-3
        self.M_H = 1e-3
        self.M_P = 500e-3
        self.M_M = 60e-3

        # fundamental constants
        self.F = 96485 # Faraday constant [J/V*mol]
        self.R = 8.314  # Gas constant [J/K*mol]
        self.eo = 8.854e-12 # permittivity of free space [F/m]
        self.kb = 1.3806e-23  # Boltzmann constant [m2 kg/ s2 K1]
        self.q = 1.602e-19    # electron charge [C]
        self.mu = 1.275e-6   # magnetic permeability [H/m or N/A2]
        self.NAv = 6.022e23     # Avagadro's Number
        self.er = 80.0          # relative dielectric constant of electrolyte
        self.eedl = 6.0         # relative dielectric constant of screening layer

        self.eedl = (
            self._conf['internal parameters']['double layer permittivity'])

        self.deltaGATP = -37000    # free energy released in ATP hydrolysis under standard phys conditions [J/mol]

        self.ac = 1.0e-6  # cell-cell separation for drawing
        self.scale_cell = 0.90          # the amount to scale cell membranes in from ecm edges (only affects drawing)
        self.cm = float(iu['membrane capacitance'])           # patch capacitance of cell membrane 0.022 [F/m2]

        self.tm = 7.5e-9           # thickness of cell membrane [m]
        self.cell_sides = 4      # minimum number of membrane domains per cell (must be >2)
        self.scale_alpha = 1.4   # the amount to scale (1/d_cell) when calculating the concave hull (boundary search)
        self.merge_cut_off = (1/50)  # the fraction of nominal cell perimeter at which nearby ecm points are merged

        self.d_cell = self.cell_radius * 2  # diameter of single cell
        self.nx = int(self.wsx / self.d_cell)  # number of lattice sites in world x index
        self.ny = int(self.wsy / self.d_cell)  # number of lattice sites in world y index
        self.wsx = self.wsx + 5 * self.cell_lattice_disorder * self.d_cell  # readjust the world size for noise
        self.wsy = self.wsy + 5 * self.cell_lattice_disorder * self.d_cell

        self.gjl = 2*self.tm + self.cell_space     # gap junction length
        self.gj_radius = 1.0e-9              # effective radius of gap junctions connecting cells [m] (range 0 to 5.0 e-9 m)

        self.um = 1e6    # multiplication factor to convert m to um

        self.isamples = 40.0  # sampling of vector data for currents

        self.rho = 1050 # mass density of system [kg/m3]

        self.fast_update_ecm = iu.get('fast update ecm', True)  # quick or slow update to cell<--> ecm grid exchange?

        self.sharpness = float(iu.get('sharpness', 0.999))

        # simplest ion profile giving realistic results with minimal ions (Na+ & K+ focus):
        if self.ion_profile is IonProfileType.BASIC:
            self.cNa_env = 145.0
            self.cK_env = 5.0
            self.cP_env = 10.0

            zs = [self.z_Na, self.z_K, self.z_P]

            conc_env = [self.cNa_env, self.cK_env, self.cP_env]
            self.conc_env_m, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 8.0
            self.cK_cell = 125.0
            self.cP_cell = 100.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cP_cell]

            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.ions_dict = {'Na':1,'K':1,'Cl':0,'Ca':0,'H':0,'P':1,'M':1}

            self.cell_concs ={'Na':self.cNa_cell,'K':self.cK_cell,'P':self.cP_cell,'M':self.cM_cell}
            self.env_concs ={'Na':self.cNa_env, 'K':self.cK_env, 'P':self.cP_env, 'M':self.conc_env_m}
            self.mem_perms = {'Na':self.Dm_Na,'K':self.Dm_K,'P':self.Dm_P,'M':self.Dm_M}
            self.ion_charge = {'Na':self.z_Na,'K':self.z_K,'P':self.z_P,'M':self.z_M}
            self.free_diff = {'Na':self.Do_Na,'K':self.Do_K,'P':self.Do_P,'M':self.Do_M}
            self.molar_mass = {'Na':self.M_Na,'K':self.M_K,'P':self.M_P,'M':self.M_M}
            self.ion_long_name = {'Na':'sodium','K':'potassium','P':'proteins','M':'anion'}

        elif self.ion_profile is IonProfileType.BASIC_CA:
            self.cNa_env = 145.0
            self.cK_env = 5.0
            self.cCa_env = 1.0
            self.cP_env = 10.0

            zs = [self.z_Na, self.z_K, self.z_Ca, self.z_P]

            conc_env = [self.cNa_env, self.cK_env, self.cCa_env, self.cP_env]
            self.conc_env_m, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 8.0
            self.cK_cell = 125.0
            self.cCa_cell = 1.0e-4
            self.cP_cell = 100.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cCa_cell, self.cP_cell]

            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.cCa_er = 0.5
            self.cM_er = self.cCa_er

            self.ions_dict = {'Na':1,'K':1,'Cl':0,'Ca':1,'H':0,'P':1,'M':1}

            self.cell_concs ={'Na':self.cNa_cell,'K':self.cK_cell,'Ca':self.cCa_cell,'P':self.cP_cell,'M':self.cM_cell}
            self.env_concs ={'Na':self.cNa_env, 'K':self.cK_env, 'Ca':self.cCa_env, 'P':self.cP_env, 'M':self.conc_env_m}
            self.mem_perms = {'Na':self.Dm_Na,'K':self.Dm_K,'Ca':self.Dm_Ca, 'P':self.Dm_P,'M':self.Dm_M}
            self.ion_charge = {'Na':self.z_Na,'K':self.z_K,'Ca':self.z_Ca, 'P':self.z_P,'M':self.z_M}
            self.free_diff = {'Na':self.Do_Na,'K':self.Do_K,'Ca':self.Do_Ca, 'P':self.Do_P,'M':self.Do_M}
            self.molar_mass = {'Na':self.M_Na,'K':self.M_K,'Ca':self.M_Ca, 'P':self.M_P,'M':self.M_M}
            self.ion_long_name = {'Na':'sodium','K':'potassium','Ca':'calcium','P':'proteins','M':'anion'}

        # default environmental and cytoplasmic initial values mammalian cells
        elif self.ion_profile is IonProfileType.MAMMAL:
            # initialize proton concentrations to "None" placeholders
            self.cNa_env = 145.0
            self.cK_env = 5.0
            self.conc_env_cl = 105.0
            self.cCa_env = 1.0
            self.cP_env = 10.0

            zs = [self.z_Na, self.z_K, self.z_Cl, self.z_Ca, self.z_P]

            conc_env = [self.cNa_env, self.cK_env, self.conc_env_cl, self.cCa_env, self.cP_env]
            self.conc_env_m, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 8.0
            self.cK_cell = 125.0
            self.cCl_cell = 20.0
            self.cCa_cell = 1.0e-4
            self.cP_cell = 100.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cCl_cell, self.cCa_cell, self.cP_cell]
            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.cCa_er = 0.5
            self.cM_er = self.cCa_er

            self.ions_dict = {'Na':1,'K':1,'Cl':1,'Ca':1,'H':0,'P':1,'M':1}

            self.cell_concs ={'Na':self.cNa_cell,'K':self.cK_cell,'Ca':self.cCa_cell,'Cl':self.cCl_cell,
                              'P':self.cP_cell,'M':self.cM_cell}

            self.env_concs ={'Na':self.cNa_env, 'K':self.cK_env, 'Ca':self.cCa_env, 'Cl':self.conc_env_cl,
                             'P':self.cP_env, 'M':self.conc_env_m}

            self.mem_perms = {'Na':self.Dm_Na,'K':self.Dm_K,'Ca':self.Dm_Ca,'Cl':self.Dm_Cl,
                              'P':self.Dm_P,'M':self.Dm_M}

            self.ion_charge = {'Na':self.z_Na,'K':self.z_K,'Ca':self.z_Ca,'Cl':self.z_Cl,
                               'P':self.z_P,'M':self.z_M}

            self.free_diff = {'Na':self.Do_Na,'K':self.Do_K,'Ca':self.Do_Ca,'Cl':self.Do_Cl,
                              'P':self.Do_P,'M':self.Do_M}

            self.molar_mass = {'Na':self.M_Na,'K':self.M_K,'Ca':self.M_Ca,'Cl':self.M_Cl,
                               'P':self.M_P,'M':self.M_M}

            self.ion_long_name = {'Na':'sodium','K':'potassium','Ca':'calcium','Cl':'chloride',
                                  'P':'proteins','M':'anion'}

        elif self.ion_profile is IonProfileType.AMPHIBIAN:
            # initialize proton concentrations to "None" placeholders
            self.cNa_env = 14.50
            self.cK_env = 0.5
            self.conc_env_cl = 10.50
            self.cCa_env = 0.2
            self.cP_env = 0.0

            zs = [self.z_Na, self.z_K, self.z_Cl, self.z_Ca, self.z_P]

            conc_env = [self.cNa_env, self.cK_env, self.conc_env_cl, self.cCa_env, self.cP_env]
            self.conc_env_m, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 8.0
            self.cK_cell = 125.0
            self.cCl_cell = 20.0
            self.cCa_cell = 1.0e-3
            self.cP_cell = 100.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cCl_cell, self.cCa_cell, self.cP_cell]
            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.cCa_er = 0.5
            self.cM_er = self.cCa_er

            self.ions_dict = {'Na':1,'K':1,'Cl':1,'Ca':1,'H':0,'P':1,'M':1}

            self.cell_concs ={'Na':self.cNa_cell,'K':self.cK_cell,'Ca':self.cCa_cell,'Cl':self.cCl_cell,
                              'P':self.cP_cell,'M':self.cM_cell}
            self.env_concs ={'Na':self.cNa_env, 'K':self.cK_env, 'Ca':self.cCa_env, 'Cl':self.conc_env_cl,
                             'P':self.cP_env, 'M':self.conc_env_m}
            self.mem_perms = {'Na':self.Dm_Na,'K':self.Dm_K,'Ca':self.Dm_Ca,'Cl':self.Dm_Cl,
                              'P':self.Dm_P,'M':self.Dm_M}
            self.ion_charge = {'Na':self.z_Na,'K':self.z_K,'Ca':self.z_Ca,'Cl':self.z_Cl,
                               'P':self.z_P,'M':self.z_M}
            self.free_diff = {'Na':self.Do_Na,'K':self.Do_K,'Ca':self.Do_Ca,'Cl':self.Do_Cl,
                              'P':self.Do_P,'M':self.Do_M}

            self.molar_mass = {'Na':self.M_Na,'K':self.M_K,'Ca':self.M_Ca,'Cl':self.M_Cl,
                               'P':self.M_P,'M':self.M_M}

            self.ion_long_name = {'Na':'sodium','K':'potassium','Ca':'calcium','Cl':'chloride',
                                  'P':'proteins','M':'anion'}

        # user-specified environmental and cytoplasm values (customized)
        elif self.ion_profile is IonProfileType.CUSTOM:
            # initialize proton concentrations to "None" placeholders
            cip = self._conf['general options']['customized ion profile']

            self.cNa_env = float(cip['extracellular Na+ concentration'])
            self.cK_env = float(cip['extracellular K+ concentration'])
            self.conc_env_cl = float(cip['extracellular Cl- concentration'])
            self.cCa_env = float(cip['extracellular Ca2+ concentration'])
            self.cP_env = float(cip['extracellular protein- concentration'])

            zs = [self.z_Na, self.z_K, self.z_Cl, self.z_Ca, self.z_P]

            conc_env = [self.cNa_env, self.cK_env, self.conc_env_cl, self.cCa_env, self.cP_env]
            self.conc_env_m, self.z_M_env = bal_charge(conc_env, zs)

            self.cNa_cell = float(cip['cytosolic Na+ concentration'])
            self.cK_cell = float(cip['cytosolic K+ concentration'])
            self.cCl_cell = float(cip['cytosolic Cl- concentration'])
            self.cCa_cell = float(cip['cytosolic Ca2+ concentration'])
            # self.cM_cell = float(cip['cytosolic HCO3- concentration'])
            self.cP_cell = float(cip['cytosolic protein- concentration'])

            conc_cell = [self.cNa_cell, self.cK_cell, self.cCl_cell, self.cCa_cell, self.cP_cell]
            self.cM_cell, self.z_M_cell = bal_charge(conc_cell, zs)

            assert self.z_M_cell == -1

            self.cCa_er = float(cip['endoplasmic reticulum Ca2+'])
            self.cM_er = self.cCa_er

            self.ions_dict = {'Na':1,'K':1,'Cl':1,'Ca':1,'H':0,'P':1,'M':1}

            self.cell_concs ={'Na':self.cNa_cell,'K':self.cK_cell,'Ca':self.cCa_cell,'Cl':self.cCl_cell, 'P':self.cP_cell,'M':self.cM_cell}

            self.env_concs ={'Na':self.cNa_env, 'K':self.cK_env, 'Ca':self.cCa_env, 'Cl':self.conc_env_cl, 'P':self.cP_env, 'M':self.conc_env_m}

            self.mem_perms = {'Na':self.Dm_Na,'K':self.Dm_K,'Ca':self.Dm_Ca,'Cl':self.Dm_Cl, 'P':self.Dm_P,'M':self.Dm_M}

            self.ion_charge = {'Na':self.z_Na,'K':self.z_K,'Ca':self.z_Ca,'Cl':self.z_Cl, 'P':self.z_P,'M':self.z_M}

            self.free_diff = {'Na':self.Do_Na,'K':self.Do_K,'Ca':self.Do_Ca,'Cl':self.Do_Cl, 'P':self.Do_P,'M':self.Do_M}

            self.molar_mass = {'Na':self.M_Na,'K':self.M_K,'Ca':self.M_Ca,'Cl':self.M_Cl, 'P':self.M_P,'M':self.M_M}

            self.ion_long_name = {'Na':'sodium','K':'potassium','Ca':'calcium','Cl':'chloride',
                                  'P':'proteins','M':'anion'}

        # Else, this ion profile type is unrecognized. Raise an exception.
        else:
            raise BetseSimConfigException(
                'Ion profile type "{}" unrecognized.'.format(self.ion_profile))

    # ..................{ INITIALIZERS ~ path                }..................
    def _init_paths(self) -> None:
        '''
        Initialize paths specified by this configuration.
        '''

        # Absolute pathname of directories specified by this configuration.
        self.init_pickle_dirname = pathnames.join_and_canonicalize(
            self.conf_dirname, self.init_pickle_dirname_relative)
        self.sim_pickle_dirname = pathnames.join_and_canonicalize(
            self.conf_dirname, self.sim_pickle_dirname_relative)

        # Absolute or relative paths of the directories containing saved
        # initialization and simulation results.
        self.init_export_dirname = pathnames.join_and_canonicalize(
            self.conf_dirname, self.init_export_dirname_relative)
        self.sim_export_dirname = pathnames.join_and_canonicalize(
            self.conf_dirname, self.sim_export_dirname_relative)

        # Create all non-existing directories.
        dirs.make_unless_dir(
            self.init_pickle_dirname, self.sim_pickle_dirname,
            self.init_export_dirname, self.sim_export_dirname)

    # ..................{ INITIALIZERS ~ tissue              }..................
    def _init_tissue_and_cut_profiles(self) -> None:
        '''
        Parse tissue and cut profile-specific parameters from the current YAML
        configuration file.
        '''

        tpd = self._conf['tissue profile definition']

        #FIXME: Refactor as follows:
        #
        #* Replace all references to this variable elsewhere in the codebase
        #  with references to the "name" variable the default tissue profile.
        #* Remove this variable entirely.
        self.default_tissue_name = (
            self._conf['tissue profile definition']['tissue']['default']['name'])

        #FIXME: Shift all such high-level objects into higher-level (and hence
        #more appropriate) simulation classes. In particular, refactor the
        #"clipping_bitmap_matcher" instance variable into a local variable of
        #the Cells._make_voronoi() method, the only method referencing this
        #variable. (Nice!)
        self.clipping_bitmap_matcher = TissuePickerImage(
            tpd['clipping']['bitmap']['file'], self.conf_dirname)

    # ..................{ EXCEPTIONS                         }..................
    def die_unless_ecm(self) -> None:
        '''
        Raise an exception unless this configuration has enabled simulation of
        the extracellular matrix and hence environmental grid spaces.
        '''

        if not self.is_ecm:
            raise BetseSimConfigException(
                'Extracellular spaces disabled by '
                'this simulation configuration.')

    # ..................{ SETTERS                            }..................
    #FIXME: Actually, this method makes little sense here; clearly, this method
    #sets phase-specific attributes. All phase-specific attributes should reside
    #directly in the "SimPhase" API rather than in this class, which is
    #supposed to be phase-agnostic and hence reusable between phases.

    @type_check
    def set_time_profile(self, phase_kind: SimPhaseKind) -> None:
        '''
        Set temporal attributes specific to the passed simulation phase type.

        These attributes include:

        * ``dt``, the duration in seconds of each time step for this phase.
        * ``total_time``, the duration in seconds of this phase.

        Parameters
        ----------
        phase_kind : SimPhaseKind
            Current simulation phase type.
        '''

        # If this simulation phase is an initialization...
        if phase_kind is SimPhaseKind.INIT:
            self.dt = self.init_time_step
            self.init_tsteps = self.init_time_total / self.dt
            self.resample = self.init_time_sampling
            self.total_time = self.init_time_total
        # Else if this simulation phase is a simulation.
        elif phase_kind is SimPhaseKind.SIM:
            self.dt = self.sim_time_step
            self.sim_tsteps = self.sim_time_total / self.dt
            self.resample = self.sim_time_sampling
            self.total_time = self.sim_time_total
        else:
            raise BetseSimPhaseException(
                'Simulation phase "{}" unsupported.'.format(phase_kind.name))

        # Number of time steps (including sampled and unsampled) between each
        # unsampled time step, including that unsampled time step itself.
        self.t_resample = self.resample / self.dt

        # Duration in seconds of the current simulation phase accelerated by
        # the current gap junction acceleration factor.
        self.total_time_accelerated = self.total_time

    # ..................{ SUPERCLASS ~ optional              }..................
    # Methods intended to be optionally overriden by subclasses.

    #FIXME: Actually implement this properly. Ideally, this method should return
    #the set of all subdirectories internally referenced by the current
    #top-level YAML file. Instead, it simply returns all subdirectories
    #internally referenced by the *DEFAULT* top-level YAML file. Why? Because
    #the latter was much easier than the former, despite being wrong. Laziness
    #prevails!
    def _iter_conf_subdirnames(self) -> IterableTypes:

        # If no file has been read, raise an exception.
        self._die_unless_loaded()

        # Default to the basenames of all direct subdirectories of the parent
        # directory containing the default simulation configuration file, which
        # are guaranteed to be required by this file.
        return dirs.iter_subdir_basenames(pathtree.get_data_yaml_dirname())

# ....................{ HELPERS                            }....................
#FIXME: Shift this into a more appropriate math-oriented module. Funny sunning!
def bal_charge(concentrations: SequenceTypes, zs: SequenceTypes) -> tuple:
    '''
    Sum the concentrations of profile ions with their charge state to
    determine how much net positive charge exists, returning the concentration
    of the charge compensation anion M- needed to have zero net charge.

    Parameters
    -------------
    concentrations : SequenceType
        Array defining the concentrations of all ions in a space.
    zs : SequenceType
        Array (in complementary order to `concentrations`) of ion valence
        state.

    Returns
    ---------
    (float, float)
        2-tuple `(bal_conc, valence)`, where:
        * `bal_conc` is the concentration of anion M- to create zero net
          charge.
        * `valence` is the charge of the `bal_conc`. Ideally, this should
          _always_ be -1.
    '''

    q = 0

    for conc,z in zip(concentrations, zs):
        q = q+ conc*z

        to_zero = -q
        bal_conc = abs(to_zero)
        valance = np.sign(to_zero)

        assert bal_conc >= 0

    return bal_conc, valance
