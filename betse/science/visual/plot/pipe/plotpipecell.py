#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
**Post-simulation single-cell plot pipelines** (i.e., pipelines plotting
simulated data of a single cell of the cell cluster).
'''

# ....................{ IMPORTS                            }....................
import numpy as np
from betse.exceptions import BetseSimConfigException
from betse.science.config.export.confvis import SimConfVisualCellListItem
from betse.science.simulate.pipe import piperunreq
from betse.science.visual.plot.pipe.plotpipeabc import PlotPipeABC
from betse.science.simulate.pipe.piperun import piperunner
from betse.science.visual.plot import plotutil
from betse.util.type.types import IterableTypes
from matplotlib import pyplot as pyplot

# ....................{ SUBCLASSES                         }....................
class PlotCellPipe(PlotPipeABC):
    '''
    **Post-simulation single-cell plot pipeline** (i.e., object iteratively
    displaying and/or saving all plots specific to a single cell of the cell
    cluster, produced after initialization and simulation as specified by the
    current simulation configuration).
    '''

    # ..................{ INITIALIZERS                       }..................
    def __init__(self, *args, **kwargs) -> None:

        # Initialize our superclass with all passed parameters.
        super().__init__(*args, label_singular='single-cell plot', **kwargs)

        # If this index is not that of an actual cell, raise an exception.
        if self._phase.p.plot_cell not in self._phase.cells.cell_i:
            raise BetseSimConfigException(
                'Plot cell index {} invalid '
                '(i.e., not in range [{}, {}]).'.format(
                    self._phase.p.plot_cell,
                    self._phase.cells.cell_i[0],
                    self._phase.cells.cell_i[-1],
                ))

    # ..................{ SUPERCLASS                         }..................
    @property
    def _runners_conf(self) -> IterableTypes:
        return self._phase.p.plot.after_sim_pipeline_cell

    # ..................{ EXPORTERS ~ cell : current         }..................
    #FIXME: Force every currently optional "conf" parameter to be mandatory.
    #Specifically, excise "= None" everywhere below.
    @piperunner(categories=('Current Density', 'Transmembrane',))
    def export_currents_membrane(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot all transmembrane current densities for the single cell indexed by
        the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        pyplot.figure()
        axI = pyplot.subplot(111)

        if self._phase.p.sim_ECM:
            # Total cell current storage vector.
            Imem = []

            # Indices of all membranes for this cell.
            mems_for_plotcell = self._phase.cells.cell_to_mems[
                self._phase.p.plot_cell]

            for t in range(len(self._phase.sim.time)):
                memArray = self._phase.sim.I_mem_time[t]

                # X and Y components of the net current at each membrane.
                Ixo = (
                    memArray[mems_for_plotcell] *
                    self._phase.cells.mem_vects_flat[mems_for_plotcell,2] *
                    self._phase.cells.mem_sa[mems_for_plotcell]
                )
                Iyo = (
                    memArray[mems_for_plotcell] *
                    self._phase.cells.mem_vects_flat[mems_for_plotcell,3] *
                    self._phase.cells.mem_sa[mems_for_plotcell]
                )

                # X and Y components of the net current over all membranes,
                # implicitly accounting for in-out directionality.
                Ix = np.sum(Ixo)
                Iy = np.sum(Iyo)

                # Current density, obtained by dividing the total magnitude of
                # the net current by this cell's surface area.
                Io = np.sqrt(Ix**2 + Iy**2) / self._phase.cells.cell_sa[
                    self._phase.p.plot_cell]
                Imem.append(100*Io)
        else:
            Imem = [
                100*memArray[self._phase.p.plot_cell]
                for memArray in self._phase.sim.I_mem_time
            ]

        axI.plot(self._phase.sim.time, Imem)
        axI.set_xlabel('Time [s]')
        axI.set_ylabel('Current density [uA/cm2]')
        axI.set_title(
            'Transmembrane current density for cell {}'.format(
                self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='Imem_time')

    # ..................{ EXPORTERS ~ cell : deform          }..................
    @piperunner(
        categories=('Physical Deformation',),
        requirements={piperunreq.DEFORM,},
    )
    def export_deform(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot all physical cellular deformations for the single cell indexed by
        the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        # Extract time-series deformation data for the plot cell.
        dx = np.asarray([
            arr[self._phase.p.plot_cell]
            for arr in self._phase.sim.dx_cell_time])
        dy = np.asarray([
            arr[self._phase.p.plot_cell]
            for arr in self._phase.sim.dy_cell_time])

        # Get the total magnitude.
        disp = np.sqrt(dx**2 + dy**2)

        pyplot.figure()
        axD = pyplot.subplot(111)
        axD.plot(self._phase.sim.time, self._phase.p.um*disp)
        axD.set_xlabel('Time [s]')
        axD.set_ylabel('Displacement [um]')
        axD.set_title('Displacement of cell {}'.format(self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='Displacement_time')

    # ..................{ EXPORTERS ~ cell : ion             }..................
    @piperunner(
        categories=('Ion Concentration', 'Calcium'),
        requirements={piperunreq.ION_CALCIUM, },
    )
    def export_ion_calcium(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot all calcium (i.e., Ca2+) ion concentrations for the single cell
        indexed by the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        figA, axA = plotutil.plotSingleCellCData(
            self._phase.sim.cc_time,
            self._phase.sim.time,
            self._phase.sim.iCa,
            self._phase.p.plot_cell,
            fig=None,
            ax=None,
            lncolor='g',
            ionname='Ca2+ cell',
        )
        axA.set_title('Cytosolic Ca2+ in cell {}'.format(
            self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='cytosol_Ca_time')


    @piperunner(
        categories=('Ion Concentration', 'M anion'),
        requirements={piperunreq.ION_M_ANION, },
    )
    def export_ion_m_anion(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot all M anion (i.e., M-) ion concentrations for the single cell
        indexed by the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        figConcsM, axConcsM = plotutil.plotSingleCellCData(
            self._phase.sim.cc_time,
            self._phase.sim.time,
            self._phase.sim.iM,
            self._phase.p.plot_cell,
            fig=None, ax=None,
            lncolor='r',
            ionname='M-',
        )
        axConcsM.set_title(
            'M Anion concentration in cell {}'.format(self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='concM_time')


    @piperunner(
        categories=('Ion Concentration', 'Potassium'),
        requirements={piperunreq.ION_POTASSIUM, },
    )
    def export_ion_potassium(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot all potassium (i.e., K+) ion concentrations for the single cell
        indexed by the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        figConcsK, axConcsK = plotutil.plotSingleCellCData(
            self._phase.sim.cc_time,
            self._phase.sim.time,
            self._phase.sim.iK,
            self._phase.p.plot_cell,
            fig=None, ax=None,
            lncolor='b',
            ionname='K+',
        )
        axConcsK.set_title(
            'Potassium concentration in cell {}'.format(
                self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='concK_time')


    @piperunner(
        categories=('Ion Concentration', 'Sodium'),
        requirements={piperunreq.ION_SODIUM, },
    )
    def export_ion_sodium(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot all sodium (i.e., Na+) ion concentrations for the single cell
        indexed by the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        # Plot cell sodium concentration versus time.
        figConcsNa, axConcsNa = plotutil.plotSingleCellCData(
            self._phase.sim.cc_time,
            self._phase.sim.time,
            self._phase.sim.iNa,
            self._phase.p.plot_cell,
            fig=None,
            ax=None,
            lncolor='g',
            ionname='Na+',
        )
        axConcsNa.set_title(
            'Sodium concentration in cell {}'.format(self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='concNa_time')

    # ..................{ EXPORTERS ~ pressure               }..................
    @piperunner(
        categories=('Pressure', 'Osmotic',),
        requirements={piperunreq.PRESSURE_OSMOTIC,},
    )
    def export_pressure_osmotic(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot the osmotic cellular pressure for the single cell indexed by the
        current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        p_osmo = tuple(
            arr[self._phase.p.plot_cell]
            for arr in self._phase.sim.osmo_P_delta_time)

        pyplot.figure()
        axOP = pyplot.subplot(111)
        axOP.plot(self._phase.sim.time, p_osmo)
        axOP.set_xlabel('Time [s]')
        axOP.set_ylabel('Osmotic Pressure [Pa]')
        axOP.set_title(
            'Osmotic pressure in cell {}'.format(self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='OsmoticP_time')


    @piperunner(
        categories=('Pressure', 'Total',),
        requirements={piperunreq.PRESSURE_TOTAL,},
    )
    def export_pressure_total(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot the **total cellular pressure** (i.e., summation of the cellular
        mechanical and osmotic pressure) for the single cell indexed by the
        current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        p_hydro = tuple(
            arr[self._phase.p.plot_cell]
            for arr in self._phase.sim.P_cells_time)

        pyplot.figure()
        axOP = pyplot.subplot(111)
        axOP.plot(self._phase.sim.time, p_hydro)
        axOP.set_xlabel('Time [s]')
        axOP.set_ylabel('Total Pressure [Pa]')
        axOP.set_title(
            'Total pressure in cell {}'.format(self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='P_time')

    # ..................{ EXPORTERS ~ cell : pump            }..................
    #FIXME: Actually plot the average of these rates. Currently, this method
    #only plots rates for a single arbitrarily selected membrane of this cell.
    @piperunner(categories=('Pump Rate', 'Na-K-ATPase',))
    def export_pump_nakatpase(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot the averages of the Na-K-ATPase membrane pump rates for the single
        cell indexed by the current simulation configuration over all time
        steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        pyplot.figure()
        axNaK = pyplot.subplot()

        if self._phase.p.sim_ECM:
            #FIXME: Generalize to average across all membranes of this cell.
            pump_array_index = self._phase.cells.cell_to_mems[
                self._phase.p.plot_cell][0]
        else:
            pump_array_index = self._phase.p.plot_cell

        pump_rate = tuple(
            pump_array[pump_array_index]
            for pump_array in self._phase.sim.rate_NaKATP_time)

        axNaK.plot(self._phase.sim.time, pump_rate)
        axNaK.set_xlabel('Time [s]')
        axNaK.set_ylabel('Pumping Rate of Na+ Out of Cell [mol/(m2 s)]')
        axNaK.set_title(
            'Rate of NaK-ATPase pump in cell: {}'.format(
                self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='NaKATPase_rate')

    # ..................{ EXPORTERS ~ cell : voltage         }..................
    #FIXME: Actually plot the average of these Vmems. Currently, this method
    #only plots Vmems for a single arbitrarily selected membrane of this cell.
    @piperunner(categories=('Voltage', 'Transmembrane', 'Average',))
    def export_voltage_membrane(self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot the averages of all transmembrane voltages for the single cell
        indexed by the current simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        #FIXME: Generalize to average across all membranes of this cell.
        mem_i = self._phase.cells.cell_to_mems[self._phase.p.plot_cell][0]

        # Plot single cell Vmem vs time.
        figVt, axVt = plotutil.plotSingleCellVData(
            self._phase.sim,
            mem_i,
            self._phase.p,
            fig=None, ax=None,
            lncolor='k',
        )
        axVt.set_title(
            'Voltage (Vmem) in cell {}'.format(self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='Vmem_time')


    #FIXME: Actually plot the average of these Vmems. Currently, this method
    #only plots Vmems for a single arbitrarily selected membrane of this cell.
    @piperunner(categories=(
        'Voltage', 'Transmembrane', 'Fast Fourier Transform (FFT)',))
    def export_voltage_membrane_fft(
        self, conf: SimConfVisualCellListItem) -> None:
        '''
        Plot the fast Fourier transform (FFT) of the averages of all
        transmembrane voltages for the single cell indexed by the current
        simulation configuration over all time steps.
        '''

        # Prepare to export the current plot.
        self._export_prep()

        #FIXME: Generalize to average across all membranes of this cell.
        mem_i = self._phase.cells.cell_to_mems[self._phase.p.plot_cell][0]

        figFFT, axFFT = plotutil.plotFFT(
            self._phase.sim.time, self._phase.sim.vm_time, mem_i, lab="Power")
        axFFT.set_title(
            'Fourier transform of Vmem in cell {}'.format(
                self._phase.p.plot_cell))

        # Export this plot to disk and/or display.
        self._export(basename='Vmem_FFT_time')