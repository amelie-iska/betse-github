#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level utility functions specific to single-frame plots.
'''

import os
import os.path

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma
from matplotlib.collections import LineCollection, PolyCollection
from scipy import interpolate

from betse.exceptions import BetseSimConfigException
from betse.util.io.log import logs
from betse.util.path import dirs
from betse.util.type import types


def plotSingleCellVData(sim,celli,p,fig=None,ax=None, lncolor='k'):

    tvect_data=[x[celli]*1000 for x in sim.vm_time]

    if fig is None:
        fig = plt.figure()# define the figure and axes instances
    if ax is None:
        ax = plt.subplot(111)

    ax.plot(sim.time, tvect_data,lncolor,linewidth=2.0)

    if p.GHK_calc is True:
        tvect_data_ghk = [x[p.plot_cell]*1000 for x in sim.vm_GHK_time]
        ax.plot(sim.time, tvect_data_ghk,'r',linewidth=2.0)

    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Voltage [mV]')

    return fig, ax

def plotSingleCellCData(simdata_time,simtime,ioni,celli,fig=None,ax=None,lncolor='b',ionname='ion'):

    # ccIon_cell = [arr[ioni][celli] for arr in simdata_time]
    ccIon_cell = []

    for carray in simdata_time:
        conc = carray[ioni][celli]
        ccIon_cell.append(conc)

    if fig is None:
        fig = plt.figure()# define the figure and axes instances
    if ax is None:
        ax = plt.subplot(111)
        #ax = plt.axes()

    lab = ionname

    ax.plot(simtime, ccIon_cell,lncolor,label=lab)
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Concentration [mol/m3]')

    return fig, ax

def plotSingleCellData(simtime,simdata_time,celli,fig=None,ax=None,lncolor='b',lab='Data'):

    data_cell = [arr[celli] for arr in simdata_time]

    if fig is None:
        fig = plt.figure()# define the figure and axes instances
    if ax is None:
        ax = plt.subplot(111)

    xmin = simtime[0]
    xmax = simtime[-1]
    ymin = np.min(data_cell)
    ymax = np.max(data_cell)

    ax.plot(simtime, data_cell,lncolor,label=lab)
    ax.set_xlabel('Time [s]')
    ax.set_ylabel(lab)

    return fig, ax

def plotFFT(simtime,simdata_time,celli,fig=None,ax=None,lncolor='b',lab='Data'):
    """
    Calculates the FFT for time-series data defined on a single cell (p.plot_cell)
    and returns a plot of the spectrum in frequency-space.

    Parameters
    -----------
    simtime:            The time vector for the plot
    simdata_time:       The full data for the plot define on all cell centres of the cluster at all sample times
    celli:              The single cell index to extract data for
    fig:                A handle to an existing figure (default None; function creates the figure)
    ax:                 Handle to an existing axis (default None; function creates the axis)
    lncolor:            Line colour for the plot
    lab:                Label for the data type (e.g. "Vmem [V]" or "Body Force [N/m3]")

    Returns
    --------
    fig, ax     Handles to the figure and axis of the FFT plot
    """

    if fig is None:
        fig = plt.figure()
    if ax is None:
        ax = plt.subplot(111)

    sample_size = len(simtime)
    sample_spacing = simtime[1] - simtime[0]

    cell_data_o = [arr[celli] for arr in simdata_time]
    # membranes_midpoint_data = ((1/sample_size)*(cell_data_o/np.mean(cell_data_o)) )   # normalize the signal
    cell_data = (1/sample_size)*(cell_data_o - np.mean(cell_data_o))

    f_axis = np.fft.rfftfreq(sample_size, d=sample_spacing)
    fft_data_o = np.fft.rfft(cell_data)
    fft_data = np.sqrt(np.real(fft_data_o)**2 + np.imag(fft_data_o)**2)

    xmin = f_axis[0]
    xmax = f_axis[-1]
    ymin = np.min(fft_data)
    ymax = np.max(fft_data)

    ax.plot(f_axis,fft_data)
    ax.axis([xmin,xmax,ymin,ymax])

    ax.set_xlabel('Frequency [1/s]')
    ax.set_ylabel('Signal Power')

    return fig, ax


def plotHetMem(sim,cells, p, fig=None, ax=None, zdata=None,clrAutoscale = True, clrMin = None, clrMax = None,
    clrmap=None,edgeOverlay = True,pointOverlay=None, number_cells = False, number_mems = False,
    number_ecm = False, current_overlay = False,plotIecm = False):
        """
        This plotting method assigns color-data to each node in the cell cluster that has distinct
        membrane domains for each cell. Data is interpolated to generate a smooth surface plot.
        The method returns a plot instance (fig, axes)

        When using p.sim_ECM, this plotting method overrides both plotPolyData and plotCellData.

        Parameters
        ----------
        zdata                  A data array with each scalar entry corresponding to a point in
                               mem_mids_flat. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html

        clrAutoscale           If True, the colorbar is autoscaled to the max and min of zdata.

        clrMin                 Sets the colorbar to a user-specified minimum value.

        clrMax                 Set the colorbar to a user-specified maximum value


        edgeOverlay             This option allows the user to specify whether or not they want cell edges overlayed.
                                Default is False, set to True to use.

        pointOverlay            This option allows user to specify whether or not they want cell_centre points plotted
                                Default is False, set to True to use.

        number_cells,           Booleans that control whether or not cell, membrane, and ecm spaces are labeled
        number_ecm,             with their indices.
        number_mems


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses `matplotlib.pyplot` and `numpy` arrays. With `edgeOverlay` and
        `pointOverlay` equal to `None`, this is computationally fast and *is*
        recommended for plotting data on large collectives.
        """

        if fig is None:
            fig = plt.figure()# define the figure and axes instances
        if ax is None:
            ax = plt.subplot(111)

        if clrmap is None:
            clrmap = p.default_cm

        if zdata is None:
            zdata = np.ones((p.plot_grid_size,p.plot_grid_size))

        ax.axis('equal')

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])

        if p.plotMask is True:
            zdata = ma.masked_array(zdata, np.logical_not(cells.maskM))

        meshplt = plt.imshow(zdata,origin='lower',extent=[xmin,xmax,ymin,ymax],cmap=clrmap)

        if pointOverlay is True:
            ax.scatter(
                p.um*cells.mem_mids_flat[:,0],
                p.um*cells.mem_mids_flat[:,1], c='k',)

        if edgeOverlay is True:
            # cell_edges_flat, _ , _= tb.flatten(cells.mem_edges)
            cell_edges_flat = p.um*cells.mem_edges_flat
            coll = LineCollection(cell_edges_flat,colors='k')
            coll.set_alpha(0.5)
            ax.add_collection(coll)

        if zdata is not None:
            # Add a colorbar for the mesh plot:
            maxval = round(np.max(1000*sim.vm_time[-1]),1)
            minval = round(np.min(1000*sim.vm_time[-1]),1)
            checkval = maxval - minval

            if checkval == 0:
                minval = minval - 0.1
                maxval = maxval + 0.1

        if zdata is not None and clrAutoscale is True:
            meshplt.set_clim(minval,maxval)
            ax_cb = fig.colorbar(meshplt,ax=ax)

        elif clrAutoscale is False:

            meshplt.set_clim(clrMin,clrMax)
            ax_cb = fig.colorbar(meshplt,ax=ax)

        else:
            ax_cb = None

        if number_cells is True:

            for i,cll in enumerate(cells.cell_centres):
                ax.text(p.um*cll[0],p.um*cll[1],i,ha='center',va='center')

        if number_mems is True:

            for i,mem in enumerate(cells.mem_mids_flat):
                ax.text(p.um*mem[0],p.um*mem[1],i,ha='center',va='center')

        if current_overlay is True:

            I_overlay(sim,cells,p,ax,plotIecm)

        return fig, ax, ax_cb


def plotPolyData(sim, cells, p, fig=None, ax=None, zdata = None, clrAutoscale = True, clrMin = None, clrMax = None,
    clrmap = None, number_cells=False, current_overlay = False,plotIecm=False):
        """
        Assigns color-data to each polygon in a cell cluster diagram and
        returns a plot instance (fig, axes).

        Parameters
        ----------
        cells : Cells
            Data structure holding all world information about cell geometry.
        zdata : optional[numpy.ndarray]
            A data array with each scalar entry corresponding to a cell's data
            value (for instance, concentration or voltage). If zdata is not
            supplied, the cells will be plotted with a uniform color; if zdata
            is the string `random`, a random data set will be created and
            plotted.
        clrAutoscale : optional[bool]
            If `True`, the colorbar is autoscaled to the max and min of zdata.
        clrMin : optional[float]
            Set the colorbar to a user-specified minimum value.
        clrMax : optional[float]
            Set the colorbar to a user-specified maximum value.
        clrmap : optional[matplotlib.cm]
            The colormap to use for plotting. Must be specified as cm.mapname.
            A list of available mapnames is supplied at:
            http://matplotlib.org/examples/color/colormaps_reference.html

        Returns
        -------
        fig, ax
            Matplotlib figure and axes instances for the plot.

        Notes
        -------
        This method Uses `matplotlib.collections.PolyCollection`,
        `matplotlib.cm`, `matplotlib.pyplot`, and numpy arrays and hence is
        computationally slow. Avoid calling this method for large collectives
        (e.g., larger than 500 x 500 um).
        """

        if fig is None:
            fig = plt.figure()# define the figure and axes instances
        if ax is None:
            ax = plt.subplot(111)
            #ax = plt.axes()

        if zdata is None:  # if user doesn't supply data
            z = np.ones(len(cells.cell_verts)) # create flat data for plotting

        #FIXME: This is a bit cumbersome. Ideally, a new "is_zdata_random"
        #boolean parameter defaulting to "False" should be tested, instead.
        #Whack-a-mole with a big-fat-pole!

        # If random data is requested, do so. To avoid erroneous and expensive
        # elementwise comparisons when "zdata" is neither None nor a string,
        # "zdata" must be guaranteed to be a string *BEFORE* testing this
        # parameter as a string. Numpy prints scary warnings otherwise: e.g.,
        #
        #     FutureWarning: elementwise comparison failed; returning scalar
        #     instead, but in the future will perform elementwise comparison
        elif isinstance(zdata, str) and zdata == 'random':
            z = np.random.random(len(cells.cell_verts)) # create some random data for plotting
        else:
            z = zdata

        # Make the polygon collection and add it to the plot.
        if clrmap is None:
            #clrmap = p.default_cm
            clrmap = cm.rainbow

        if p.showCells is True:
            coll, ax = cell_mosaic(z,ax,cells,p,p.default_cm)
        else:
            coll, ax = cell_mesh(z,ax,cells,p,p.default_cm)

        # points = np.multiply(cells.cell_verts, p.um)
        #
        # coll = PolyCollection(points, array=z, cmap=clrmap, edgecolors='none')
        # ax.add_collection(coll)
        ax.axis('equal')

        # Add a colorbar for the PolyCollection

        if zdata is not None and clrAutoscale is True:
            maxval = np.max(zdata,axis=0)
            minval = np.min(zdata,axis=0)

            coll.set_clim(minval,maxval)
            ax_cb = fig.colorbar(coll,ax=ax)

        elif clrAutoscale is False and zdata is not None:
            coll.set_clim(clrMin,clrMax)
            ax_cb = fig.colorbar(coll,ax=ax)

        elif zdata is None:
            ax_cb = None

        if number_cells is True:
            for i,cll in enumerate(cells.cell_centres):
                ax.text(p.um*cll[0],p.um*cll[1],i,ha='center',va='center')

        if current_overlay is True:
            streams, ax = I_overlay(sim,cells,p,ax,plotIecm)

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])

        return fig,ax,ax_cb

def plotPrettyPolyData(data, sim, cells, p, fig=None, ax=None, clrAutoscale = True, clrMin = None, clrMax = None,
    clrmap = None, number_cells=False, current_overlay = False,plotIecm=False):
        """
        Assigns color-data to each polygon mem-mid, vertex and cell centre in a cell cluster
        diagram and returns a plot instance (fig, axes).

        Parameters
        ----------
        cells : Cells
            Data structure holding all world information about cell geometry.
        data : [numpy.ndarray]
            A data array with each scalar entry corresponding to a cell's data
            value (for instance, concentration or voltage) at cell membranes. If zdata is not
            supplied, the cells will be plotted with a uniform color; if zdata
            is the string `random`, a random data set will be created and
            plotted.
        clrAutoscale : optional[bool]
            If `True`, the colorbar is autoscaled to the max and min of zdata.
        clrMin : optional[float]
            Set the colorbar to a user-specified minimum value.
        clrMax : optional[float]
            Set the colorbar to a user-specified maximum value.
        clrmap : optional[matplotlib.cm]
            The colormap to use for plotting. Must be specified as cm.mapname.
            A list of available mapnames is supplied at:
            http://matplotlib.org/examples/color/colormaps_reference.html

        Returns
        -------
        fig, ax
            Matplotlib figure and axes instances for the plot.

        Notes
        -------
        This method Uses `matplotlib.collections.PolyCollection`,
        `matplotlib.cm`, `matplotlib.pyplot`, and numpy arrays and hence is
        computationally slow. Avoid calling this method for large collectives
        (e.g., larger than 500 x 500 um).
        """

        if fig is None:
            fig = plt.figure()# define the figure and axes instances
        if ax is None:
            ax = plt.subplot(111)

        # data processing -- map to verts:
        data_verts = np.dot(data, cells.matrixMap2Verts)

        # define colorbar limits for the PolyCollection

        if clrAutoscale is True:
            maxval = data_verts.max()
            minval = data_verts.min()
            # maxval = data_verts.max()
            # minval = data_verts.min()

        else:
            maxval = clrMax
            minval = clrMin


        # Make the polygon collection and add it to the plot.
        if clrmap is None:
            clrmap = p.default_cm

        if p.showCells is True:
            coll, ax = pretty_patch_plot(
                data_verts,ax,cells,p,p.default_cm, cmin=minval, cmax=maxval)
        else:
            coll, ax = cell_mesh(data,ax,cells,p,p.default_cm)

        # add a colorbar
        coll.set_clim(minval, maxval)
        ax_cb = fig.colorbar(coll, ax=ax)

        ax.axis('equal')

        if number_cells is True:
            for i,cll in enumerate(cells.cell_centres):
                ax.text(p.um*cll[0],p.um*cll[1],i,ha='center',va='center')

        if current_overlay is True:
            streams, ax = I_overlay(sim,cells,p,ax,plotIecm)

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])

        return fig,ax,ax_cb

def plotVectField(Fx,Fy,cells,p,plot_ecm = False,title = 'Vector field',cb_title = 'Field [V/m]',
                    colorAutoscale = True, minColor = None, maxColor=None):

    fig = plt.figure()
    ax = plt.subplot(111)

    if plot_ecm is True:

        efield = np.sqrt(Fx**2 + Fy**2)

        msh = ax.imshow(efield,origin='lower', extent = [cells.xmin*p.um, cells.xmax*p.um, cells.ymin*p.um,
            cells.ymax*p.um],cmap=p.background_cm)

        vplot, ax = env_quiver(Fx,Fy,ax,cells,p)

        tit_extra = 'Extracellular'

    elif plot_ecm is False:

        efield = np.sqrt(Fx**2 + Fy**2)

        msh, ax = cell_mesh(efield,ax,cells,p,p.background_cm)

        vplot, ax = cell_quiver(Fx,Fy,ax,cells,p)

        tit_extra = 'Intracellular'

    ax.axis('equal')

    xmin = cells.xmin*p.um
    xmax = cells.xmax*p.um
    ymin = cells.ymin*p.um
    ymax = cells.ymax*p.um

    ax.axis([xmin,xmax,ymin,ymax])

    if colorAutoscale is False:
        msh.set_clim(minColor,maxColor)

    cb = fig.colorbar(msh)

    tit = title
    ax.set_title(tit)
    ax.set_xlabel('Spatial distance [um]')
    ax.set_ylabel('Spatial distance [um]')
    cb.set_label(cb_title)

    return fig, ax, cb

def plotStreamField(
    Fx,Fy,
    cells,
    p,
    plot_ecm: bool = False,
    title: str = 'Vector field',
    cb_title: str = 'Field [V/m]',
    show_cells: bool = False,
    colorAutoscale: bool = True,
    minColor = None,
    maxColor = None,
):

    fig = plt.figure()
    ax = plt.subplot(111)

    if plot_ecm is True:
        efield = np.sqrt(Fx**2 + Fy**2)
        # msh = ax.imshow(
        #     efield,
        #     origin='lower',
        #     extent=[cells.xmin*p.um, cells.xmax*p.um, cells.ymin*p.um, cells.ymax*p.um],
        #     cmap=p.background_cm,
        # )
        splot, ax = env_stream(Fx,Fy,ax,cells,p, cmap=p.background_cm)
        tit_extra = 'Extracellular'

    elif plot_ecm is False:
        efield = np.sqrt(Fx**2 + Fy**2)
        # msh, ax = cell_mesh(efield,ax,cells,p,p.background_cm)
        splot, ax = cell_stream(Fx,Fy,ax,cells,p,showing_cells=show_cells,cmap=p.background_cm)
        tit_extra = 'Intracellular'

    ax.axis('equal')

    xmin = cells.xmin*p.um
    xmax = cells.xmax*p.um
    ymin = cells.ymin*p.um
    ymax = cells.ymax*p.um

    ax.axis([xmin,xmax,ymin,ymax])

    if colorAutoscale is False:
        splot.lines.set_clim(minColor,maxColor)

    cb = fig.colorbar(splot.lines)

    tit = title
    ax.set_title(tit)
    ax.set_xlabel('Spatial distance [um]')
    ax.set_ylabel('Spatial distance [um]')
    cb.set_label(cb_title)

    return fig, ax, cb

def plotMemData(cells, p, fig= None, ax = None, zdata=None,clrmap=None):
        """

        Assigns color-data to edges in a 2D Voronoi diagram and returns a plot instance (fig, axes)

        Parameters
        ----------
        zdata_t                  A data array with each scalar entry corresponding to a polygon entry in
                               vor_verts. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.collections LineCollection, matplotlib.cm, matplotlib.pyplot and numpy arrays
        Computationally slow -- not recommended for large collectives (500 x 500 um max)

        """

        if fig is None:
            fig = plt.figure()# define the figure and axes instances
        if ax is None:
            ax = plt.subplot(111)

        cell_edges_flat = p.um*cells.mem_edges_flat

        if zdata is None:
            z = np.ones(len(cell_edges_flat))
        #FIXME: This is a bit cumbersome. Ideally, a new "is_zdata_random"
        #boolean parameter defaulting to "False" should be tested, instead.
        #Whack-a-mole with a big-fat-pole!

        # If random data is requested, do so. To avoid erroneous and expensive
        # elementwise comparisons when "zdata" is neither None nor a string,
        # "zdata" must be guaranteed to be a string *BEFORE* testing this
        # parameter as a string. Numpy prints scary warnings otherwise: e.g.,
        #
        #     FutureWarning: elementwise comparison failed; returning scalar
        #     instead, but in the future will perform elementwise comparison
        elif isinstance(zdata, str) and zdata == 'random':
            z = np.random.random(len(cell_edges_flat))
        else:
            z = zdata

        if clrmap is None:
            clrmap = cm.rainbow

        coll = LineCollection(cell_edges_flat, array=z, cmap=clrmap,linewidths=4.0)
        ax.add_collection(coll)

        # coll.set_clim(0,3)

        ax.axis('equal')

        # Add a colorbar for the Line Collection
        if zdata is not None:
            ax_cb = fig.colorbar(coll, ax=ax)

        ax.axis('equal')

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])

        return fig, ax, ax_cb

def plotConnectionData(cells, p, fig = None, ax=None, zdata=None,clrmap=None,colorbar = None, pickable=None):
        """
        Assigns color-data to connections between a cell and its nearest neighbours and returns plot instance

        Parameters
        ----------

        zdata_t                  A data array with each scalar entry corresponding to a polygon entry in
                               vor_verts. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.collections LineCollection, matplotlib.cm, matplotlib.pyplot and numpy arrays

        """
        if fig is None:
            fig = plt.figure()# define the figure and axes instances
        if ax is None:
            ax = plt.subplot(111)
            #ax = plt.axes()

        if zdata is None:
            z = np.ones(len(cells.gap_jun_i))
        #FIXME: This is a bit cumbersome. Ideally, a new "is_zdata_random"
        #boolean parameter defaulting to "False" should be tested, instead.
        #Whack-a-mole with a big-fat-pole!

        # If random data is requested, do so. To avoid erroneous and expensive
        # elementwise comparisons when "zdata" is neither None nor a string,
        # "zdata" must be guaranteed to be a string *BEFORE* testing this
        # parameter as a string. Numpy prints scary warnings otherwise: e.g.,
        #
        #     FutureWarning: elementwise comparison failed; returning scalar
        #     instead, but in the future will perform elementwise comparison
        elif isinstance(zdata, str) and zdata == 'random':
            z = np.random.random(len(cells.gap_jun_i))

        else:
            z = zdata

        if clrmap is None:
            clrmap = cm.bone_r  # default colormap

         # Make a line collection and add it to the plot.

        con_segs = cells.cell_centres[cells.gap_jun_i]

        connects = p.um*np.asarray(con_segs)

        coll = LineCollection(connects, array=z, cmap=clrmap, linewidths=4.0, zorder=0)
        coll.set_clim(vmin=0.0,vmax=1.0)
        coll.set_picker(pickable)
        ax.add_collection(coll)

        ax.axis('equal')

        # Add a colorbar for the Line Collection
        if zdata is not None and colorbar == 1:
            ax_cb = fig.colorbar(coll, ax=ax)
        else:
            ax_cb = None

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])

        return fig, ax, ax_cb

def plotBoundCells(points_flat,bflags,cells, p, fig=None, ax=None):
        """
        Plot elements tagged on the boundary as red points.

        Parameters
        ----------
        points_flat          A flat array of points corresponding to the bflags data structure

        bflags          A nested array of boolean flags indicating boundary tagging

        Returns
        -------
        fig, ax         Matplotlib plotting objects

        Note
        ------
        This particular plot is extremely slow -- intended for cross-checking purposes only!

        """
        if fig is None:
            fig = plt.figure()# define the figure and axes instances
        if ax is None:
            ax = plt.subplot(111)
            #ax = plt.axes()

        points_flat = np.asarray(points_flat)
        bflags = np.asarray(bflags)

        bpoints = points_flat[bflags]

        ax.plot(p.um*points_flat[:,0],p.um*points_flat[:,1],'k.')

        ax.plot(p.um*bpoints[:,0],p.um*bpoints[:,1],'r.')

        # cell_edges_flat, _ , _= tb.flatten(cells.mem_edges)
        cell_edges_flat = p.um*cells.mem_edges_flat
        coll = LineCollection(cell_edges_flat,colors='k')
        coll.set_alpha(0.5)
        ax.add_collection(coll)

        ax.axis('equal')

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])

        return fig, ax

def plotVects(cells, p, fig=None, ax=None):
        """
        This function plots all unit vectors in the tissue system as a cross-check.
        Normals to cell membranes are shown as red arrows.
        Tangents to cell membranes are black arrows.
        Tangents to ecm edges are shown as green arrows.
        Cell membrane edges are drawn as blue lines.

        To plot streamline and vector plots with data use the pyplot quiver and streamplot functions, respectively.

        """

        if fig is None:
            fig = plt.figure()# define the figure and axes instances

        if ax is None:
            ax = plt.subplot(111)
            #ax = plt.axes()

        s = p.um

        ax.quiver(s*cells.mem_vects_flat[:,0],s*cells.mem_vects_flat[:,1],s*cells.mem_vects_flat[:,4],
                  s*cells.mem_vects_flat[:,5],color='b',label='mem tang')
        ax.quiver(s*cells.mem_vects_flat[:,0],s*cells.mem_vects_flat[:,1],s*cells.mem_vects_flat[:,2],
                  s*cells.mem_vects_flat[:,3],color='g',label ='mem norm')
        # ax.quiver(s*cells.ecm_vects[:,0],s*cells.ecm_vects[:,1],s*cells.ecm_vects[:,2],s*cells.ecm_vects[:,3],color='r')

        # cell_edges_flat, _ , _= tb.flatten(cells.mem_edges)
        cell_edges_flat = p.um*cells.mem_edges_flat
        coll = LineCollection(cell_edges_flat,colors='k')
        ax.add_collection(coll)

        ax.axis('equal')

        xmin = cells.xmin*p.um
        xmax = cells.xmax*p.um
        ymin = cells.ymin*p.um
        ymax = cells.ymax*p.um

        ax.axis([xmin,xmax,ymin,ymax])
        plt.legend()

        return fig, ax

def streamingCurrent(
    sim, cells, p,
    fig=None,
    ax=None,
    plot_Iecm=True,
    zdata=None,
    clrAutoscale=True,
    clrMin=None,
    clrMax=None,
    clrmap=cm.coolwarm,
    edgeOverlay=True,
    number_cells=False,
):

    # Define the figure and axes instances if needed.
    if fig is None:
        fig = plt.figure()
    if ax is None:
        ax = plt.subplot(111)

    ax.axis('equal')

    xmin = cells.xmin*p.um
    xmax = cells.xmax*p.um
    ymin = cells.ymin*p.um
    ymax = cells.ymax*p.um

    ax.axis([xmin,xmax,ymin,ymax])

    #FIXME: There's a fair amount of overlap between the following branches.
    #Treetops swaying in the contumely breeze!
    if p.sim_ECM is False or plot_Iecm is False:

        # multiply by 100 to get units of uA/m2
        Jmag_M = 100*np.sqrt(
            sim.I_gj_x_time[-1]**2 + sim.I_gj_y_time[-1]**2) + 1e-30

        J_x = sim.I_gj_x_time[-1]/Jmag_M
        J_y = sim.I_gj_y_time[-1]/Jmag_M

        meshplot = plt.imshow(
            Jmag_M,
            origin='lower',
            extent=[xmin,xmax,ymin,ymax],
            cmap=clrmap,
        )

        ax.streamplot(
            cells.X*p.um, cells.Y*p.um, J_x, J_y,
            density=p.stream_density,
            linewidth=(3.0*Jmag_M/Jmag_M.max()) + 0.5,
            color='k',
            cmap=clrmap,
            arrowsize=1.5,
        )

        ax.set_title('Final gap junction current density')

    elif plot_Iecm is True:
        # multiply by 100 to get units of uA/m2
        Jmag_M = 100*np.sqrt(
            sim.I_tot_x_time[-1]**2 + sim.I_tot_y_time[-1]**2) + 1e-30

        J_x = sim.I_tot_x_time[-1]/Jmag_M
        J_y = sim.I_tot_y_time[-1]/Jmag_M

        meshplot = plt.imshow(
            Jmag_M,
            origin='lower',
            extent=[xmin,xmax,ymin,ymax],
            cmap=clrmap,
        )

        ax.streamplot(
            cells.X*p.um, cells.Y*p.um, J_x, J_y,
            density=p.stream_density,
            linewidth=(3.0*Jmag_M/Jmag_M.max()) + 0.5,
            color='k',
            cmap=clrmap,
            arrowsize=1.5,
        )

        ax.set_title('Final total currents')

    if clrAutoscale is True:
        ax_cb = fig.colorbar(meshplot,ax=ax)

    elif clrAutoscale is False:
        meshplot.set_clim(clrMin,clrMax)
        ax_cb = fig.colorbar(meshplot,ax=ax)

    # if p.showCells is True:
    #     # cell_edges_flat, _ , _= tb.flatten(cells.mem_edges)
    #     cell_edges_flat = p.um*cells.mem_edges_flat
    #     coll = LineCollection(cell_edges_flat,colors='k')
    #     coll.set_alpha(0.2)
    #     ax.add_collection(coll)

    if number_cells is True:

        for i,cll in enumerate(cells.cell_centres):
            ax.text(p.um*cll[0],p.um*cll[1],i,ha='center',va='center')

    return fig,ax,ax_cb

def clusterPlot(p, dyna, cells, clrmap=cm.jet):

    fig = plt.figure()
    ax = plt.subplot(111)

    # profile_names = list(p.profiles.keys())

    col_dic = {}

    cb_ticks = []
    cb_tick_labels = []

    base_points = np.multiply(cells.cell_verts, p.um)

    z = np.zeros(len(base_points))
    z[:] = 0

    cb_ticks.append(0)
    cb_tick_labels.append(p.default_tissue_name)

    col_dic['base'] = PolyCollection(
        base_points, array=z, cmap=clrmap, edgecolors='none')
    ax.add_collection(col_dic['base'])

    if len(dyna.tissue_profile_names):
        for i, name in enumerate(dyna.tissue_profile_names):
            cell_inds = dyna.cell_target_inds[name]

            if len(cell_inds):

                points = np.multiply(cells.cell_verts[cell_inds], p.um)

                z = np.zeros(len(points))
                z[:] = i + 1

                col_dic[name] = PolyCollection(
                    points, array=z, cmap=clrmap, edgecolors='none')
                col_dic[name].set_clim(0, len(dyna.tissue_profile_names))

                # col_dic[name].set_alpha(0.8)
                col_dic[name].set_zorder(p.profiles[name]['z order'])
                ax.add_collection(col_dic[name])

                # Add this profile name to the colour legend.
                cb_ticks.append(i+1)
                cb_tick_labels.append(name)

            else:

                logs.log_warning("No cells tagged for profile " + name)



    #FIXME: Refactor into a new SimEventCut.plot() method. Beans and fragrance!
    if p.plot_cutlines and p.scheduled_options['cuts'] is not None:
        # For each profile cutting a subset of the cell population...
        for cut_profile_name in p.scheduled_options['cuts'].profile_names:
            cut_profile = p.profiles[cut_profile_name]

            # Indices of all cells cut by this profile.
            cut_cell_indices = cut_profile.picker.get_cell_indices(
                cells, p, ignoreECM=True)

            points = np.multiply(cells.cell_verts[cut_cell_indices], p.um)
            col_dic[cut_profile_name] = PolyCollection(
                points, color='k', cmap=clrmap, edgecolors='none')

            # col_dic[name].set_clim(0,len(dyna.tissue_profile_names) + len(names))
            # col_dic[name].set_alpha(0.8)

            col_dic[cut_profile_name].set_zorder(cut_profile.z_order)
            ax.add_collection(col_dic[cut_profile_name])

            #FIXME: Interestingly, this doesn't appear to do anything. I have
            #no idea why. The matpotlib is weak with me. Legends and old elves!

            # Add this profile name to the colour legend.
            cb_tick_next = len(cb_ticks)
            cb_ticks.append(cb_tick_next)
            cb_tick_labels.append(cut_profile_name)

    ax_cb = None
    if len(dyna.tissue_profile_names):
        ax_cb = fig.colorbar(
            col_dic[dyna.tissue_profile_names[0]], ax=ax, ticks=cb_ticks)
        ax_cb.ax.set_yticklabels(cb_tick_labels)

    if p.enumerate_cells is True:
        for i, cll in enumerate(cells.cell_centres):
            ax.text(
                p.um*cll[0], p.um*cll[1], i,
                ha='center', va='center', zorder=20)

    ax.set_xlabel('Spatial Distance [um]')
    ax.set_ylabel('Spatial Distance [um]')
    ax.set_title('Cell Cluster')

    ax.axis('equal')

    xmin = cells.xmin*p.um
    xmax = cells.xmax*p.um
    ymin = cells.ymin*p.um
    ymax = cells.ymax*p.um

    ax.axis([xmin,xmax,ymin,ymax])

    return fig, ax, ax_cb

#FIXME: Shift this function into a new data-specific submodule -- say,
#"betse.science.data.datacsv". Data is an appropriate terse noun encapsulating
#the concept of both resulting data and exported data.
#FIXME: Rename this function to save_cell_time_series().
#FIXME: Refactor this function to accept only a single "SimPhaseABC" instance.
def exportData(cells,sim,p):

    #FIXME: Refactor the following five lines to simply read:
    #
    #    # Create the top-level directory containing these exports if needed.
    #    dirs.make_unless_dir(phase.save_dirname)
    if p.plot_type is 'sim':
        results_path = p.sim_results
    elif p.plot_type is 'init':
        results_path = p.init_results
    os.makedirs(results_path, exist_ok=True)

    savedData = os.path.join(results_path, 'ExportedData.csv')
    savedData_FFT = os.path.join(results_path, 'ExportedData_FFT.csv')

    cc_cell = []

    dd_cell = []

    ci = p.plot_cell  # index of cell to get time data for

    # create the header, first entry will be time:
    headr = 'time_s'
    t = np.asarray(sim.time)

    #-----------Vmem----------------------------------------------

    # next entry will be Vm:
    headr = headr + ',' + 'Vmem_mV'

    if p.sim_ECM is False:
        vm = [arr[ci]*1000 for arr in sim.vm_time]

    else:
        vm = []
        for vm_at_mem in sim.vm_time:
            vm_t = 1000*cell_ave(cells,vm_at_mem)[ci]
            vm.append(vm_t)

    vm = np.asarray(vm)

    # golman Vmem------------------------------------------------------

    if p.GHK_calc is True:

        vm_goldman = [x[p.plot_cell]*1000 for x in sim.vm_GHK_time]

    else:
        vm_goldman = np.zeros(len(sim.time))

    vm_goldman = np.asarray(vm_goldman)
    # next entry will be Vm:
    headr = headr + ',' + 'Goldman_Vmem_mV'

    # ------Na K pump rate-----------------------------------------------

    # Na-K-pump rate:
    if p.sim_ECM is False:
        pump_rate = [pump_array[p.plot_cell] for pump_array in sim.rate_NaKATP_time]

    else:
        pump_rate = [pump_array[cells.cell_to_mems[p.plot_cell][0]] for pump_array in sim.rate_NaKATP_time]

    pump_rate = np.asarray(pump_rate)
    headr = headr + ',' + 'NaK-ATPase_Rate_mol/m2s'

    #----------cell concentrations---------------------------------------

    # create the header starting with cell concentrations
    for i in range(0,len(sim.ionlabel)):
        label = sim.ionlabel[i]
        headr = headr + ',' + 'cell_' + label + '_mmol/L'
        cc_m = [arr[i][ci] for arr in sim.cc_time]
        cc_m = np.asarray(cc_m)
        cc_cell.append(cc_m)


    cc_cell = np.asarray(cc_cell)

    #----------membrane permeabilities---------------------------------------

    # create the header starting with membrane permeabilities
    if p.sim_ECM is False:
        for i in range(0,len(sim.ionlabel)):
            label = sim.ionlabel[i]
            headr = headr + ',' + 'Dm_' + label + '_m2/s'
            dd_m = [arr[i][ci] for arr in sim.dd_time]
            dd_m = np.asarray(dd_m)
            dd_cell.append(dd_m)

    else:
        for i in range(0,len(sim.ionlabel)):
            label = sim.ionlabel[i]
            headr = headr + ',' + 'Dm_' + label + '_m2/s'
            dd_m = [arr[i][cells.cell_to_mems[ci][0]] for arr in sim.dd_time]
            dd_m = np.asarray(dd_m)
            dd_cell.append(dd_m)


    dd_cell = np.asarray(dd_cell)

    #----Transmembrane currents--------------------------
    if p.sim_ECM is False:
        Imem = [memArray[p.plot_cell] for memArray in sim.I_mem_time]
    else:
        Imem = [memArray[cells.cell_to_mems[p.plot_cell][0]] for memArray in sim.I_mem_time]

    headr = headr + ',' + 'I_A/m2'

    #----Hydrostatic pressure--------
    p_hydro = [arr[p.plot_cell] for arr in sim.P_cells_time]

    headr = headr + ',' + 'HydroP_Pa'

    # ---Osmotic pressure-----------
    if p.deform_osmo is True:

        p_osmo = [arr[p.plot_cell] for arr in sim.osmo_P_delta_time]

    else:
        p_osmo = np.zeros(len(sim.time))

    headr = headr + ',' + 'OsmoP_Pa'

    # total deformation ---------------------------------------
    if p.deformation is True and sim.run_sim is True:

        # extract time-series deformation data for the plot cell:
        dx = np.asarray([arr[p.plot_cell] for arr in sim.dx_cell_time])
        dy = np.asarray([arr[p.plot_cell] for arr in sim.dy_cell_time])

        # get the total magnitude:
        disp = p.um*np.sqrt(dx**2 + dy**2)

    else:
        disp = np.zeros(len(sim.time))

    headr = headr + ',' + 'Displacement_um'

    # # cluster polarization vector------------------------------
    # polar_x = sim.Pol_tot_x_time
    # headr = headr + ',' + 'Polarization x_C/m'
    # polar_y = sim.Pol_tot_y_time
    # headr = headr + ',' + 'Polarization y_C/m'


    # FFT of voltage :
    sample_size = len(sim.time)
    sample_spacing = sim.time[1] - sim.time[0]

    cell_data = (1/sample_size)*(vm - np.mean(vm))

    f_axis = np.fft.rfftfreq(sample_size, d=sample_spacing)
    fft_data_o = np.fft.rfft(cell_data)
    fft_data = np.sqrt(np.real(fft_data_o)**2 + np.imag(fft_data_o)**2)

    dataM = np.column_stack((t,vm,vm_goldman,pump_rate,cc_cell.T, dd_cell.T,
                             p_hydro,p_osmo,disp))

    headr2 = 'frequency_Hz'
    headr2 = headr2 + ',' + 'FFT_Vmem'

    dataFFT = np.column_stack((f_axis,fft_data))

    np.savetxt(savedData,dataM,delimiter = ',',header = headr)
    np.savetxt(savedData_FFT,dataFFT,delimiter = ',',header = headr2)

#FIXME: Shift this function to the same "betse.science.data.datacsv" submodule.
#FIXME: Rename this function to save_cells_vmem().
def export2dData(
    i,
    simdata,
    cells,
    p,
    foldername: str = 'Vmem2D_TextExport',
    filebit: str = 'Vmem2D_',
):

    if p.plot_type == 'sim':
        results_path =  p.sim_results

    elif p.plot_type == 'init':
        results_path = p.init_results

    filename = filebit + str(i) + '.csv'

    filepath = os.path.join(results_path, foldername)

    os.makedirs(filepath, exist_ok=True)
    savedData_2d = os.path.join(filepath, filename)

    dataM = np.column_stack((p.um*cells.cell_centres[:,0], p.um*cells.cell_centres[:,1], simdata))
    hdr = 'x [um], y [um], Vmem [mV]'
    np.savetxt(savedData_2d,dataM,delimiter=',', header = hdr)

def I_overlay(sim,cells,p,ax,plotIecm = False):
    """
    Plots an overlay of simulated currents on an existing plot.

    Parameters
    -----------

    sim         Instance of sim module
    cells       Instance of cells module
    p           Instance of parameters module
    ax          Existing figure axis to plot currents on
    plotIecm    Plot total currents (True) or only those of gap junctions (False)

    Returns
    --------
    streams             Container for streamline plot
    ax                  Modified axis
    """

    if p.sim_ECM is False or plotIecm is False:

        Ix = sim.I_cell_x_time[-1]
        Iy = sim.I_cell_y_time[-1]

        streams, ax = cell_stream(Ix, Iy,ax,cells,p)

        ax.set_title('(Intracellular current overlay)')

    elif plotIecm is True:

        Ix = sim.I_tot_x_time[-1]
        Iy = sim.I_tot_y_time[-1]

        streams, ax = env_stream(Ix, Iy,ax,cells,p)

        ax.set_title('(Environment current overlay)')

    return streams, ax


def cell_ave(cells,vm_at_mem):

    """
    Averages Vmem over membrane domains to return a mean value for each cell

    Parameters
    ----------
    cells               An instance of the Cells module cells object
    vm_at_mem           Vmem at individual membrane domains


    Returns
    --------
    v_cell              Cell Vm averaged over the whole cell

    """

    v_cell = []

    for i in cells.cell_i:
        cellinds = (cells.mem_to_cells == i).nonzero()
        v_cell_array = vm_at_mem[cellinds]
        v_cell_ave = np.mean(v_cell_array)
        v_cell.append(v_cell_ave)

    v_cell = np.asarray(v_cell)

    return v_cell

# utility functions------------------------------------------------------
def cell_quiver(datax, datay, ax, cells, p):
    """
    Sets up a vector plot for cell-specific data on an existing axis.

    Parameters
    -----------

    datax, datay    Data defined on cell centres or membrane midpoints
    cells           Instance of cells module
    p               Instance of parameters module
    ax              Existing figure axis to plot currents on

    Returns
    --------
    vplot               Container for vector plot, plotted at cell centres
    ax                  Modified axis

    """

    if len(datax) == len(cells.mem_i):

        Fx = np.dot(cells.M_sum_mems,datax)/cells.num_mems
        Fy = np.dot(cells.M_sum_mems,datay)/cells.num_mems

    else:
        Fx = datax
        Fy = datay

    Fmag = np.sqrt(Fx**2 + Fy**2)

    # normalize the data:
    if Fmag.all() != 0.0:
        Fx = Fx/Fmag
        Fy = Fy/Fmag

    vplot = ax.quiver(p.um*cells.cell_centres[:,0],p.um*cells.cell_centres[:,1],Fx,Fy,
        pivot='mid',color = p.vcolor, units='x',headwidth=5, headlength = 7, zorder=10)

    return vplot, ax


def env_quiver(datax,datay,ax,cells,p):
    """
    Sets up a vector plot for environmental data on an existing axis.

    Parameters
    -----------

    datax, datay    Data defined on environmental grid
    cells           Instance of cells module
    p               Instance of parameters module
    ax              Existing figure axis to plot currents on

    Returns
    --------
    vplot               Container for vector plot, plotted at environmental grid points
    ax                  Modified axis

    """
    F_mag = np.sqrt(datax**2 + datay**2)

    if F_mag.max() != 0.0:
        Fx = datax/F_mag.max()
        Fy = datay/F_mag.max()

    else:
        Fx = datax/F_mag.mean()
        Fy = datay/F_mag.mean()

    vplot = ax.quiver(p.um*cells.xypts[:,0], p.um*cells.xypts[:,1], Fx.ravel(),
        Fy.ravel(), pivot='mid',color = p.vcolor, units='x',headwidth=5, headlength = 7,zorder=10)

    return vplot, ax

def cell_stream(datax,datay,ax,cells,p,showing_cells = False, cmap=None):
    """
    Sets up a streamline plot for cell-specific data on an existing axis.

    Parameters
    -----------

    datax, datay    Data defined on cell centres or membrane midpoints
    cells           Instance of cells module
    p               Instance of parameters module
    ax              Existing figure axis to plot currents on

    Returns
    --------
    streams             Container for stream plot, plotted at plot grid
    ax                  Modified axis

    """



    if showing_cells is True:
        cell_edges_flat = p.um*cells.mem_edges_flat
        coll = LineCollection(cell_edges_flat,colors='k')
        coll.set_alpha(0.3)
        ax.add_collection(coll)

    if datax.shape != cells.X.shape: # if the data hasn't been interpolated yet...

        Fx = interpolate.griddata((cells.cell_centres[:,0],cells.cell_centres[:,1]),datax,(cells.X,cells.Y),
                                              fill_value=0,method=p.interp_type)

        Fx = Fx*cells.maskECM

        Fy = interpolate.griddata((cells.cell_centres[:,0],cells.cell_centres[:,1]),datay,(cells.X,cells.Y),
                                              fill_value=0,method=p.interp_type)

        Fy = Fy*cells.maskECM

    else:

        Fx = datax
        Fy = datay

    Fmag = np.sqrt(Fx**2 + Fy**2) + 1e-30


    # normalize the data:
    if Fmag.all() != 0:
        Fx = Fx/Fmag
        Fy = Fy/Fmag

    if Fmag.max() != 0.0:
        lw = (3.0*Fmag/Fmag.max()) + 0.5

    else:
        lw = 3.0

    if cmap is None:

        stream_color = p.vcolor

    else:
        stream_color = Fmag

    streams = ax.streamplot(
        cells.X*p.um,
        cells.Y*p.um,
        Fx, Fy,
        density=p.stream_density,
        linewidth=lw,
        color=stream_color,
        arrowsize=1.5,
        cmap = cmap
    )

    return streams, ax


def env_stream(datax,datay,ax,cells,p, cmap=None):
    """
    Sets up a streamline plot for environmental data on an existing axis.

    Parameters
    -----------

    datax, datay    Data defined on environmental grid
    cells           Instance of cells module
    p               Instance of parameters module
    ax              Existing figure axis to plot currents on

    Returns
    --------
    streams             Container for stream plot
    ax                  Modified axis

    """

    Fmag = np.sqrt(datax**2 + datay**2) + 1e-30

    if Fmag.all() != 0.0:
        Fx = datax/Fmag
        Fy = datay/Fmag

    if Fmag.max() != 0.0:

        lw = (3.0*Fmag/Fmag.max()) + 0.5

    else:
        lw = 3.0

    # if datax.shape == cells.X.shape:

    streams = ax.streamplot(cells.X*p.um,cells.Y*p.um, Fx, Fy,density=p.stream_density,
            linewidth=lw,color=Fmag,arrowsize=1.5,cmap=cmap)

    # elif datax.shape == cells.X.shape:
    #
    #     streams = ax.streamplot(cells.X*p.um,cells.Y*p.um, Fx, Fy,density=p.stream_density,
    #         linewidth=lw,color=p.vcolor,arrowsize=1.5)

    # else:
    #     raise BetseFunctionException("Data input to env_streams function must be \n shaped as cells.X or cells.Xgrid.")

    return streams, ax


#FIXME: Fix us up, please. This function is effectively broken at the moment,
#plotting a spatially symmetric distribution even where the underlying data is
#asymmetric (in which case one would hope for some sort of distinct gradient).
#This function is frequently leveraged elsewhere and hence fairly critical.
def cell_mesh(data, ax, cells, p, clrmap):

    # If the data is defined on membrane midpoints, average to cell centres.
    if len(data) == len(cells.mem_i):
        data = np.dot(cells.M_sum_mems,data)/cells.num_mems

    data_grid = np.zeros(len(cells.voronoi_centres))
    data_grid[cells.cell_to_grid] = data

    msh = ax.tripcolor(
        p.um*cells.voronoi_centres[:,0],
        p.um*cells.voronoi_centres[:,1],
        data_grid,
        shading='gouraud',
        cmap=clrmap,
    )

    return msh, ax

#FIXME: Obsoleted by the more general-purpose, reliable, and efficient
#"betse.science.plot.layer.plottershaded.LayerCellsGouraudShaded" class.
#Replace all remaining calls to this function with usage of that class; then,
#remove this function.
def pretty_patch_plot(
    data_verts, ax, cells, p, clrmap,
    cmin=None,
    cmax=None,
    use_other_verts=None
):
    """
    Maps data on mem midpoints to vertices, and
    uses tripcolor on every cell patch to create a
    lovely gradient. Slow but beautiful!

    data:   mem midpoint data for plotting (e.g vm)
    ax:     plot axis
    cells:  cells object
    p:      parameters object
    clrmap: colormap
    cmin, cmax   clim values for the data's colormap

    """


    # data_verts = data

    # colormap clim
    if cmin is None:
        amin = data_verts.min()
        amax = data_verts.max()
    else:
        amin = cmin
        amax = cmax

    # amin = amin + 0.1 * np.abs(amin)
    # amax = amax - 0.1 * np.abs(amax)

    # collection of cell patchs at vertices:
    if use_other_verts is None:
        cell_faces = np.multiply(cells.cell_verts, p.um)
    else:
        cell_faces = np.multiply(use_other_verts, p.um)

    # Cell membrane (Vmem) plotter (slow but beautiful!)
    for i in range(len(cell_faces)):
        x = cell_faces[i][:, 0]
        y = cell_faces[i][:, 1]

        # Average color value of each cell membrane, situated at the midpoint
        # of that membrane. This parameter is referred to as "C" in both the
        # documentation and implementation of the tripcolor() function.
        dati = data_verts[cells.cell_to_mems[i]]

        # "matplotlib.collections.TriMesh" instance providing the
        # Gouraud-shaded triangulation mesh for the non-triangular vertices of
        # this cell from the Delaunay hull of these vertices.
        col_cell = ax.tripcolor(x, y, dati, shading='gouraud', cmap=clrmap)

        #FIXME: No need to manually call set_clim() here. Instead, pass the
        #"vmin=amin, vmax=amax" parameters to the above tripcolor() call.

        # Autoscale this mesh's colours as desired.
        col_cell.set_clim(amin, amax)

    return col_cell, ax


def env_mesh(data, ax, cells, p, clrmap, ignore_showCells=False):
    """
    Sets up a mesh plot for environmental data on an existing axis.

    Parameters
    -----------

    data            Data defined on environmental grid
    cells           Instance of cells module
    p               Instance of parameters module
    ax              Existing figure axis to plot currents on

    Returns
    --------
    mesh_plot           Container for mesh plot
    ax                  Modified axis

    """

    # if p.plotMask is True:
    #     data = ma.masked_array(data, np.logical_not(cells.maskM))

    mesh_plot = ax.imshow(data,origin='lower',
                extent=[p.um*cells.xmin,p.um*cells.xmax,p.um*cells.ymin,p.um*cells.ymax],cmap=clrmap)

    if p.showCells is True and ignore_showCells is False:
        cell_edges_flat = p.um*cells.mem_edges_flat
        coll = LineCollection(cell_edges_flat,colors='k')
        coll.set_alpha(0.5)
        ax.add_collection(coll)

    return mesh_plot, ax


def cell_mosaic(
    data,
    ax: 'matplotlib.axes.Axes',
    cells: 'Cells',
    p: 'Parameters',
    clrmap: 'matplotlib.colors.Colormap',
) -> (PolyCollection, 'matplotlib.axes.Axes'):
    """
    Sets up a mosaic plot for cell data on an existing axis.

    Parameters
    -----------
    data            Data defined on environmental grid
    cells           Instance of cells module
    p               Instance of parameters module
    ax              Existing figure axis to plot currents on

    Returns
    --------
    collection          Container for mosaic plot
    ax                  Modified axis
    """

    # define a polygon collection based on individual cell polygons
    points = np.multiply(cells.cell_verts, p.um)
    collection =  PolyCollection(points, cmap=clrmap, edgecolors='none')
    collection.set_array(data)
    ax.add_collection(collection)

    return collection, ax

# ....................{ PRIVATE                            }....................
#FIXME: Obsolete. Let's excise! And exercise in the sweaty eventide!
def _setup_file_saving(ani_obj: 'Anim', p: 'Parameters') -> None:
    '''
    Setup operating-system friendly file saving for animation classes.

    Parameters
    -----------
    ani_obj : Anim
        Instance of an animation class.
    p : Parameters
        Instance of the 'Parameters' class.
    '''
    assert types.is_parameters(p), types.assert_not_parameters(p)

    if p.plot_type == 'sim':
        images_dirname = os.path.join(p.sim_results, ani_obj.saveFolder)

    elif p.plot_type == 'init':
        images_dirname = os.path.join(p.init_results, ani_obj.saveFolder)

    else:
        raise BetseSimConfigException(
            'Anim saving for phase "{}" unsupported.'.format(p.plot_type))

    #FIXME: Refactor all calls to os.makedirs() everywhere similarly.

    # Make this directory if not found -- FIXME can we get rid of the printout from this function...?
    images_dirname = dirs.canonicalize_and_make_unless_dir(images_dirname)

    # Absolute or relative path of the file to be saved.
    ani_obj.savedAni = os.path.join(images_dirname, ani_obj.saveFile)

    # Force animations to *NOT* repeat (don't FIXME-- we don't want to keep saving the animation over and over and over so please keep this!)
    ani_obj.ani_repeat = False
