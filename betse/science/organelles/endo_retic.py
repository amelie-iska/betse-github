#!/usr/bin/env python3
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

"""

Creates an ER (endoplasmic reticulum) class, which includes ER-specific pumps, channels, and specific methods
relating to calcium dynamics including calcium induced calcium release controlled by inositol-triphosphate.
This class also contains the facilities to initialize, define the core computations for a simulation loop,
remove ER during a cutting event, save and report on data, and plot.

"""

import os
import os.path
import numpy as np
from betse.science import toolbox as tb
from betse.science import sim_toolbox as stb
from betse.util.io.log import logs
import matplotlib.pyplot as plt
from betse.exceptions import BetseExceptionParameters
from betse.science.plot import plot as viz
from betse.science.plot.anim.anim import AnimCellsTimeSeries, AnimEnvTimeSeries
import copy


class EndoRetic(object):

    def __init__(self, sim, cells, p):

        # init basic fields
        self.er_vol = 0.1*cells.cell_vol     # er volume
        self.er_sa = 1.0*cells.cell_sa      # er surface areas
        self.Ver = 2.0e-3*np.ones(sim.cdl)   # initial trans-membrane voltage for er
        self.Q = np.zeros(sim.cdl)     # total charge in mit
        self.cm_er = self.er_sa*p.cm    # mit membrane capacitance

        sim.cc_er = copy.deepcopy(sim.cc_cells)    # ion concentrations
        sim.cc_er[sim.iCa][:] = 0.1                # initial concentration in the ER
        self.Dm_er = copy.deepcopy(sim.cc_cells)    # membrane permeability

        for arr in self.Dm_er:

            arr[:] = 1.0e-18                 # membrane permeability altered so all are minimal

        self.Dm_er[sim.iK] = 1.0e-16   # add a K+ leak channel...

        self.Dm_er_base = copy.deepcopy(self.Dm_er)  # copies of Dm for ion channel dynamics
        self.Dm_channels = copy.deepcopy(self.Dm_er)

        self.zer = copy.deepcopy(sim.cc_cells)

        for i, arr in enumerate(self.zer):
            arr[:] = sim.zs[i]

    def get_v(self, sim, p):

        self.Q = stb.get_charge(sim.cc_er, self.zer, self.er_vol, p)
        self.Ver = (1/self.cm_er)*self.Q

    def update(self, sim, cells, p):

        if p.run_sim:

            self.channels(sim, cells, p)

        # run SERCA pump:
        f_CaATP = stb.pumpCaER(sim.cc_er[sim.iCa], sim.cc_cells[sim.iCa], self.Ver, sim.T, p)

        # update with flux
        sim.cc_cells[sim.iCa] = sim.cc_cells[sim.iCa] - f_CaATP * (self.er_sa / cells.cell_vol) * p.dt
        sim.cc_er[sim.iCa] = sim.cc_er[sim.iCa] + f_CaATP * (self.er_sa / self.er_vol) * p.dt

        for i in sim.movingIons:

            IdCM = np.ones(sim.cdl)

            f_ED = stb.electroflux(sim.cc_cells[i], sim.cc_er[i], self.Dm_er[i], p.tm*IdCM, sim.zs[i]*IdCM,
                self.Ver, sim.T, p, rho=1)

            # update with flux
            sim.cc_cells[i] = sim.cc_cells[i] - f_ED*(self.er_sa/cells.cell_vol)*p.dt
            sim.cc_er[i] = sim.cc_er[i] + f_ED*(self.er_sa/self.er_vol)*p.dt

        self.get_v(sim, p)

        # print(1e3*self.Ver.mean(), sim.cc_er[sim.iCa].mean(), sim.cc_cells[sim.iCa].mean())



    def channels(self, sim, cells, p):

        # Dm_mod_mol = self.gating_max_val * tb.hill(sim.cc_cells[sim.iCa], self.gating_Hill_K, self.gating_Hill_n)
        cCa_act = (sim.cc_cells[sim.iCa]/p.act_Km_Ca)**p.act_n_Ca
        cCa_inh = (sim.cc_cells[sim.iCa] /p.inh_Km_Ca)**p.inh_n_Ca

        Dm_mod_mol = (cCa_act/(1+cCa_act))*(1/(1+cCa_inh))

        if p.molecules_enabled:

            if 'IP3' in sim.molecules.molecule_names:
                cIP3_act = (sim.molecules.IP3.c_cells/p.act_Km_IP3)**p.act_n_IP3

                Dm_mod_mol = (cCa_act/(1 + cCa_act))*(1/(1 + cCa_inh))*(cIP3_act/(1+cIP3_act))

        print(Dm_mod_mol[p.plot_cell], self.Ver[p.plot_cell], sim.cc_er[sim.iCa][p.plot_cell], sim.cc_cells[sim.iCa][p.plot_cell])

        self.Dm_channels[sim.iCa] = p.max_er*sim.rho_channel * Dm_mod_mol

        self.Dm_er = self.Dm_er_base + self.Dm_channels

    def clear_cache(self):

        self.ver_time = []
        self.Ca_er_time = []

    def write_cache(self, sim):

        self.ver_time.append(1*self.Ver)
        self.Ca_er_time.append(1*sim.cc_er[sim.iCa][:])

    def plot_er(self, sim, cells, p):

        er_ca = [arr[p.plot_cell] for arr in self.Ca_er_time]

        plt.figure()
        plt.plot(sim.time, er_ca)

        if p.autosave is True:
            savename = self.imagePath + 'CaER_' + '.png'
            plt.savefig(savename, format='png', transparent=True)

        if p.turn_all_plots_off is False:
            plt.show(block=False)

        #-----------------------------------------------------
        er_v = [arr[p.plot_cell] for arr in self.ver_time]

        plt.figure()
        plt.plot(sim.time, er_v)

        if p.autosave is True:
            savename = self.imagePath + 'VER_' + '.png'
            plt.savefig(savename, format='png', transparent=True)

        if p.turn_all_plots_off is False:
            plt.show(block=False)

    def init_saving(self, cells, p, plot_type = 'init', nested_folder_name = 'ER'):

        # init files
        if p.autosave is True:

            if plot_type == 'sim':
                results_path = os.path.join(p.sim_results, nested_folder_name)
                p.plot_type = 'sim'

            elif plot_type == 'init':
                results_path = os.path.join(p.init_results, nested_folder_name)
                p.plot_type = 'init'

            self.resultsPath = os.path.expanduser(results_path)
            os.makedirs(self.resultsPath, exist_ok=True)

            self.imagePath = os.path.join(self.resultsPath, 'fig_')


    def remove_ers(self, sim, target_inds_cell):

        # remove cells from the mit voltage list:
        ver2 = np.delete(self.Ver, target_inds_cell)
        # reassign the new data vector to the object:
        self.Ver = ver2

        erv2 = np.delete(self.er_vol, target_inds_cell)
        self.er_vol = erv2

        erca2 = np.delete(self.er_sa, target_inds_cell)
        self.er_sa = erca2

        Q2 = np.delete(self.Q, target_inds_cell)
        self.Q = Q2

        cm2 = np.delete(self.cm_er, target_inds_cell)
        self.cm_er = cm2

        cc_er2 = []

        for i, arr in enumerate(sim.cc_er):

            # remove cells from the mit ion array in sim:
            arr2 = np.delete(arr, target_inds_cell)
            cc_er2.append(arr2)

        sim.cc_er = np.asarray(cc_er2)

        der1 = []
        der2 = []
        der3 = []
        zer = []

        for i, arr in enumerate(self.Dm_er):

            arr2 = np.delete(arr, target_inds_cell)
            der2.append(arr2)

        self.Dm_er = np.asarray(der2)

        for i, arr in enumerate(self.Dm_er_base):

            arr2 = np.delete(arr, target_inds_cell)
            der1.append(arr2)

        self.Dm_er_base = np.asarray(der1)

        for i, arr in enumerate(self.Dm_channels):

            arr2 = np.delete(arr, target_inds_cell)
            der3.append(arr2)

        self.Dm_channels = np.asarray(der3)

        for i, arr in enumerate(self.zer):

            arr2 = np.delete(arr, target_inds_cell)
            zer.append(arr2)

        self.zer = np.asarray(zer)