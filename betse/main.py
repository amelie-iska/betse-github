#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

#FIXME; Configure me for CLI usage. Note that I'm no longer convinced that the
#way we launched "yppy" (e.g., "bin/yppy.bash") was ideal. We really want to do 
#the "Pythonic" thing here. ruamel.yaml, for example, installs a Python wrapper
#"/usr/lib/yaml" which (in order):
#
#* Finds an appropriate Python interpreter.
#* Replaces the current process with the result of interpreting
#  "/usr/lib/python-exec/python${PYTHON_VERSION}/yaml". Such file appears to be
#  autogenerated by setuptools at installation time.
#FIXME; Hmm: it looks like we want a new file "betse/__main__.py" resembling:
#    from betse.main import main
#    main()
#This then permits betse to be run as follows:
#    # Yes, you either have to be in the parent directory of the directory
#    # containing such "__main__.py" file *OR* you have to fiddle with
#    # ${PYTHONPATH}.
#    >>> cd ~/py/betse
#    >>> python -m betse
#Naturally, this lends itself well to shell scripting. (Yay!)
#FIXME; Wo! Even nicer. setuptools has implicit support for "__main__.py"-style
#entry points. We just need a "setup.py" resembling:
#    setup(
#        # [...]
#        entry_points={
#            'betse': ['betse = betse.main:main'],
#        },
#    )
#What's sweet about this is that we can define additional separate scripts with
#deeper entry points if we need and or want to.

import numpy as np
import scipy as sp
import scipy.spatial as sps
import matplotlib.pyplot as plt
from matplotlib.path import Path
import math
import time
from matplotlib import collections as col
from betse.science import parameters, world
import matplotlib.cm as cm
from matplotlib.collections import LineCollection, PolyCollection

def main():
    start_time = time.time()  # get a start value for timing the simulation

    # Define numerical constants for world set-up and simulation

    const = parameters.Parameters()  # define the object that holds main parameters
    const.wsx = 100e-6  # the x-dimension of the world space [m] recommended range 50 to 1000 um
    const.wsy = 100e-6  # the y-dimension of the world space [m] recommended range 50 to 1000 um
    const.rc = 5e-6  # radius of single cell
    const.dc = const.rc * 2  # diameter of single cell
    const.nx = int(const.wsx / const.dc)  # number of lattice sites in world x index
    const.ny = int(const.wsy / const.dc)  # number of lattice sites in world y index
    const.ac = 1e-6  # cell-cell separation for drawing
    const.dc = const.rc * 2  # cell diameter
    const.nl = 0.8  # noise level for the lattice
    const.wsx = const.wsx + 5 * const.nl * const.dc  # readjust the world size for noise
    const.wsy = const.wsy + 5 * const.nl * const.dc
    const.search_d =1.5     # distance to search for nearest neighbours (relative to cell diameter dc) min 1.0 max 5.0
    const.scale_cell = 0.9          # the amount to scale cell membranes in from ecm edges (only affects drawing)
    const.cell_sides = 4      # minimum number of membrane domains per cell (must be >2)
    const.scale_alpha = 1.0   # the amount to scale (1/d_cell) when calculating the concave hull (boundary search)
    const.cell_height = 5.0e-6  # the height of a cell in the z-direction (for volume and surface area calculations)
    const.cell_space = 26.0e-9  # the true cell-cell spacing (width of extracellular space)

    cells = world.World(const, vorclose='circle',worldtype='full')
    cells.makeWorld()

    fig2, ax2, axcb2 = cells.plotPolyData(clrmap = cm.coolwarm,zdata='random')
    ax2.set_ylabel('Spatial y [m]')
    ax2.set_xlabel('Spatial x [m]')
    ax2.set_title('Concentration of Foo Ion in Each Discrete Cell')
    axcb2.set_label('Foo concentration [mol/m3]')
    plt.show(block=False)

    fig3, ax3, axcb3 = cells.plotMemData(clrmap = cm.coolwarm,zdata='random')
    ax3.set_ylabel('Spatial y [um]')
    ax3.set_xlabel('Spatial x [um]')
    ax3.set_title('Foo Voltage on Discrete Membrane Domains')
    axcb3.set_label('Foo membrane voltage [V]')
    plt.show(block=False)

    fig4, ax4, axcb4 =cells.plotConnectionData(zdata='random', clrmap=None)
    ax4.set_ylabel('Spatial y [um]')
    ax4.set_xlabel('Spatial x [um]')
    ax4.set_title('Foo GJ permeability on Cell-Cell Connections')
    axcb4.set_label('Foo GJ permeability [m/s]')
    plt.show(block=False)

    fig5, ax5, axcb5 = cells.plotVertData(cells.cell_verts,zdata='random',pointOverlay=True,edgeOverlay=True)
    ax5.set_ylabel('Spatial y [um]')
    ax5.set_xlabel('Spatial x [um]')
    ax5.set_title('Foo Voltage of Membrane Domains Interpolated to Surface Plot')
    axcb5.set_label('Foo membrane voltage [V]')
    plt.show(block=False)

    fig6, ax6 = cells.plotBoundCells(cells.mem_mids,cells.bflags_mems)
    ax6.set_ylabel('Spatial y [um]')
    ax6.set_xlabel('Spatial x [um]')
    ax6.set_title('Membrane Domains Flagged at Cluster Boundary (red points)')
    plt.show(block=False)

    fig7, ax7 = cells.plotBoundCells(cells.ecm_verts,cells.bflags_ecm)
    ax7.set_ylabel('Spatial y [um]')
    ax7.set_xlabel('Spatial x [um]')
    plt.show(block=False)

    fig8,ax8 = cells.plotVects()
    ax8.set_ylabel('Spatial y [um]')
    ax8.set_xlabel('Spatial x [um]')
    ax8.set_title('Normal and Tangent Vectors to Membrane Domains')
    plt.show(block=False)

    fig9, ax9, axcb9 = cells.plotCellData(zdata='random',pointOverlay=False,edgeOverlay=False)
    ax9.set_ylabel('Spatial y [um]')
    ax9.set_xlabel('Spatial x [um]')
    ax9.set_title('Foo Concentration in Cells Interpolated to Surface Plot')
    axcb9.set_label('Foo concentration [mol/m3]')
    plt.show(block=False)

    fig, ax = plt.subplots()
    goop = 15                           # interested in the goopth cell

    cellpt = cells.cell_centres[goop]   # get its centre point
    ax.plot(cellpt[0],cellpt[1],'ko')

    #cellverts = np.asarray(cells.cell_verts[goop])   # get the vertex points of the cell
    #ax.plot(cellverts[:,0],cellverts[:,1])

    memedges = np.asarray(cells.mem_edges[goop])   # get the list of membrane edges

    ecmverts = np.asarray(cells.ecm_verts[goop])  # get the vertices of ecm points surrounding the cell
    ax.plot(ecmverts[:,0],ecmverts[:,1],'g.')

    cellgjs = cells.cell2GJ_map[goop]

    neighcells = cells.cell_centres[cells.gap_jun_i[cellgjs]]
    coll = LineCollection(neighcells, colors='r')
    ax.add_collection(coll)

    coll2 = LineCollection(memedges,colors='b')
    ax.add_collection(coll2)

    cellecms_inds = cells.cell2ecm_map[goop]

    cellecm_verts = cells.ecm_verts_flat[cells.ecm_edges_i[cellecms_inds]]

    coll3 = LineCollection(cellecm_verts,colors='g')
    ax.add_collection(coll3)

    cellecm_mids = cells.ecm_mids[cellecms_inds]
    ax.plot(cellecm_mids[:,0],cellecm_mids[:,1],'go')

    memvects = []
    for i, mem in enumerate(memedges):
        flatind = cells.rindmap_mem[goop][i]
        memvects.append(cells.mem_vects_flat[flatind])

    ecmvects = []
    for val in cellecms_inds:
        ecmvects.append(cells.ecm_vects_flat[val])

    memvects = np.asarray(memvects)
    ecmvects = np.asarray(ecmvects)

    ax.quiver(memvects[:,0],memvects[:,1],memvects[:,2],memvects[:,3],color='b')
    ax.quiver(ecmvects[:,0],ecmvects[:,1],ecmvects[:,2],ecmvects[:,3],color='g')

    plt.show(block = False)

    print('total cell number', cells.cell_number)
    print('average neighbours', int(cells.average_nn))
    print('The simulation took', time.time() - start_time, 'seconds to complete')

    plt.show()

if __name__ == '__main__':
    main()

# --------------------( WASTELANDS                         )--------------------
