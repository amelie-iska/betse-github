#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''`betse`'s command line interface (CLI).'''

#FIXME SES: Refactor to leverage argparse.

# ....................{ IMPORTS                            }....................
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import math
import sys, time
from betse.science.world import World
from betse.science.compute import Simulator
from betse.science.parameters import Parameters

# ....................{ MAIN                               }....................
def main(args = None):
    '''Run betse`'s command line interface (CLI).

    Parameters
    ----------
    args : list, optional
        List of zero or more arguments passed to such interface (e.g., from the
        command line) or `None` if called as the entry point in an external
        script installed by `setuptools`.
    '''
    # If called from a setuptools-installed script, copy such arguments from the
    # argument list excluding the first item of such list. By cross-platform
    # agreement, such item is *ALWAYS* the command name of the current process
    # (e.g., "betse") and hence ignorable.
    if args is None:
        args = sys.argv[1:]

    start_time = time.time()  # get a start value for timing the simulation

    # cells = World(vorclose='circle',worldtype='full')
    # cells.makeWorld()
    #
    p = Parameters()
    sim = Simulator()

#    sim.baseInit(cells,p)
#    sim.runInit(cells,p)
    cells, _ = sim.loadInit()

    # p.sim_tsteps = 1000
    # p.gjsa = math.pi*(2.5e-9)**2

    sim.runSim(cells,p)
#    cells,p = sim.loadSim()

    vdata = sim.vm_time[-1]*1000
    #vdata =sim.vm_check*1000

    fig2, ax2, axcb2 = cells.plotPolyData(clrmap = cm.coolwarm,zdata=vdata)
    ax2.set_ylabel('Spatial y [m]')
    ax2.set_xlabel('Spatial x [m]')
    ax2.set_title('Voltage in Each Discrete Cell')
    axcb2.set_label('Voltage [mV]')
    plt.show(block=False)

    ioni = sim.iNa
    cdata = sim.cc_time[-1][ioni]
    ionname = sim.ionlabel[ioni]

    fig3, ax3, axcb3 = cells.plotPolyData(clrmap = cm.coolwarm,zdata=cdata)
    ax3.set_ylabel('Spatial y [m]')
    ax3.set_xlabel('Spatial x [m]')
    ax3.set_title((ionname,'Concentration in Cells'))
    axcb3.set_label((ionname,'[mol/m3]'))
    plt.show(block=False)

    ioni = sim.iK
    cdata = sim.cc_time[-1][ioni]
    ionname = sim.ionlabel[ioni]

    fig4, ax4, axcb4 = cells.plotPolyData(clrmap = cm.coolwarm,zdata=cdata)
    ax4.set_ylabel('Spatial y [m]')
    ax4.set_xlabel('Spatial x [m]')
    ax4.set_title((ionname,'Concentration in Cells'))
    axcb4.set_label((ionname,'[mol/m3]'))
    plt.show(block=False)

    # fig3, ax3, axcb3 = cells.plotMemData(clrmap = cm.coolwarm,zdata='random')
    # ax3.set_ylabel('Spatial y [um]')
    # ax3.set_xlabel('Spatial x [um]')
    # ax3.set_title('Foo Voltage on Discrete Membrane Domains')
    # axcb3.set_label('Foo membrane voltage [V]')
    # plt.show(block=False)
    #
    # fig4, ax4, axcb4 =cells.plotConnectionData(zdata='random', clrmap=None)
    # ax4.set_ylabel('Spatial y [um]')
    # ax4.set_xlabel('Spatial x [um]')
    # ax4.set_title('Foo GJ permeability on Cell-Cell Connections')
    # axcb4.set_label('Foo GJ permeability [m/s]')
    # plt.show(block=False)
    #
    # fig5, ax5, axcb5 = cells.plotVertData(cells.cell_verts,zdata='random',pointOverlay=True,edgeOverlay=True)
    # ax5.set_ylabel('Spatial y [um]')
    # ax5.set_xlabel('Spatial x [um]')
    # ax5.set_title('Foo Voltage of Membrane Domains Interpolated to Surface Plot')
    # axcb5.set_label('Foo membrane voltage [V]')
    # plt.show(block=False)
    #
    # fig6, ax6 = cells.plotBoundCells(cells.mem_mids_flat,cells.bflags_mems)
    # ax6.set_ylabel('Spatial y [um]')
    # ax6.set_xlabel('Spatial x [um]')
    # ax6.set_title('Membrane Domains Flagged at Cluster Boundary (red points)')
    # plt.show(block=False)
    #
    # fig7, ax7 = cells.plotBoundCells(cells.ecm_verts_unique,cells.bflags_ecm)
    # ax7.set_ylabel('Spatial y [um]')
    # ax7.set_xlabel('Spatial x [um]')
    # plt.show(block=False)
    #
    # fig8,ax8 = cells.plotVects()
    # ax8.set_ylabel('Spatial y [um]')
    # ax8.set_xlabel('Spatial x [um]')
    # ax8.set_title('Normal and Tangent Vectors to Membrane Domains')
    # plt.show(block=False)
    #
    # fig9, ax9, axcb9 = cells.plotCellData(zdata='random',pointOverlay=False,edgeOverlay=False)
    # ax9.set_ylabel('Spatial y [um]')
    # ax9.set_xlabel('Spatial x [um]')
    # ax9.set_title('Foo Concentration in Cells Interpolated to Surface Plot')
    # axcb9.set_label('Foo concentration [mol/m3]')
    # plt.show(block=False)

    # fig, ax = plt.subplots()
    # goop = 15                           # interested in the goopth cell
    #
    # cellpt = cells.cell_centres[goop]   # get its centre point
    # ax.plot(cellpt[0],cellpt[1],'ko')
    #
    # #cellverts = np.asarray(cells.cell_verts[goop])   # get the vertex points of the cell
    # #ax.plot(cellverts[:,0],cellverts[:,1])
    #
    # memedges = np.asarray(cells.mem_edges[goop])   # get the list of membrane edges
    #
    # ecmverts = np.asarray(cells.ecm_verts[goop])  # get the vertices of ecm points surrounding the cell
    # ax.plot(ecmverts[:,0],ecmverts[:,1],'g.')
    #
    # cellgjs = cells.cell2GJ_map[goop]
    #
    # neighcells = cells.cell_centres[cells.gap_jun_i[cellgjs]]
    #
    # coll = LineCollection(neighcells, colors='r')
    # ax.add_collection(coll)
    #
    # coll2 = LineCollection(memedges,colors='b')
    # ax.add_collection(coll2)
    #
    # cellecms_inds = cells.cell2ecm_map[goop]
    #
    # cellecm_verts = cells.ecm_verts_unique[cells.ecm_edges_i[cellecms_inds]]
    #
    # coll3 = LineCollection(cellecm_verts,colors='g')
    # ax.add_collection(coll3)
    #
    # cellecm_mids = cells.ecm_mids[cellecms_inds]
    # ax.plot(cellecm_mids[:,0],cellecm_mids[:,1],'go')
    #
    # memvects = []
    # for i, mem in enumerate(memedges):
    #     flatind = cells.rindmap_mem[goop][i]
    #     memvects.append(cells.mem_vects_flat[flatind])
    #
    # ecmvects = []
    # for val in cellecms_inds:
    #     ecmvects.append(cells.ecm_vects[val])
    #
    # memvects = np.asarray(memvects)
    # ecmvects = np.asarray(ecmvects)
    #
    # ax.quiver(memvects[:,0],memvects[:,1],memvects[:,2],memvects[:,3],color='b')
    # ax.quiver(ecmvects[:,0],ecmvects[:,1],ecmvects[:,2],ecmvects[:,3],color='g')
    #
    # plt.show(block = False)

    print('total cell number', cells.cell_number)
    print('average neighbours', int(cells.average_nn))
    print('The simulation took', time.time() - start_time, 'seconds to complete')

    plt.show()

# --------------------( WASTELANDS                         )--------------------
# if __name__ == '__main__':
#     main()

#FUXME; Configure me for CLI usage. Note that I'm no longer convinced that the
#way we launched "yppy" (e.g., "bin/yppy.bash") was ideal. We really want to do
#the "Pythonic" thing here. ruamel.yaml, for example, installs a Python wrapper
#"/usr/lib/yaml" which (in order):
#
#* Finds an appropriate Python interpreter.
#* Replaces the current process with the result of interpreting
#  "/usr/lib/python-exec/python${PYTHON_VERSION}/yaml". Such file appears to be
#  autogenerated by setuptools at installation time.
#FUXME; Hmm: it looks like we want a new file "betse/__main__.py" resembling:
#    from betse.main import main
#    main()
#This then permits betse to be run as follows:
#    # Yes, you either have to be in the parent directory of the directory
#    # containing such "__main__.py" file *OR* you have to fiddle with
#    # ${PYTHONPATH}.
#    >>> cd ~/py/betse
#    >>> python -m betse
#Naturally, this lends itself well to shell scripting. (Yay!)
#FUXME; Wo! Even nicer. setuptools has implicit support for "__main__.py"-style
#entry points. We just need a "setup.py" resembling:
#    setup(
#        # [...]
#        entry_points={
#            'betse': ['betse = betse.main:main'],
#        },
#    )
#What's sweet about this is that we can define additional separate scripts with
#deeper entry points if we need and or want to.
