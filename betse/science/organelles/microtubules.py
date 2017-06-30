#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

"""
**Microtubules** (i.e., vectors aligned in the direction of endogenous current
flux through cells) functionality.
"""

import numpy as np
from betse.exceptions import BetseSimInstabilityException
from betse.util.io.log import logs
from betse.science.math import modulate as mods


class Mtubes(object):
    '''
    Object encapsulating all cellular microtubules for the cell cluster
    simulated at the current time step.

    Attributes
    ----------
    mtubes_x : ndarray
        One-dimensional Numpy array indexing each cell membrane such that each
        element is the normalized X component of the microtubule unit vector
        spatially situated at the midpoint of that membrane for this time step.
    mtubes_y : ndarray
        One-dimensional Numpy array indexing each cell membrane such that each
        element is the normalized Y component of the microtubule unit vector
        spatially situated at the midpoint of that membrane for this time step.
    mtubes_xo : ndarray
        One-dimensional Numpy array indexing each cell membrane such that each
        element is the non-normalized X component of the microtubule vector
        spatially situated at the midpoint of that membrane for this time step.
    mtubes_yo : ndarray
        One-dimensional Numpy array indexing each cell membrane such that each
        element is the non-normalized Y component of the microtubule vector
        spatially situated at the midpoint of that membrane for this time step.
    '''

    def __init__(self, sim, cells, p):

        # basic parameters for microtubule units:
        tubulin_mass = 1.66e-27 * 1e3 * 100    # kg (assumes tubulin mass of ~ 50 kDa)
        self.tubulin_length = 4.5e-9                # in meters

        self.rmt = 12.0e-9 # radius of a microtubule

        self.tubulin_N = (cells.R.mean()/self.tubulin_length) # total number of tubulin molecules

        self.charge_mtube = self.tubulin_N * p.tubulin_charge * p.q  # charge on the microtubule

        self.visc = p.cytoplasm_viscocity   # viscocity of cytoplasm

        # microtubule dipole moment [C m] (assumed to be sum of tubulin dimer dipole moments, which are 1740 D each):
        self.p_mtube = self.tubulin_N * p.tubulin_dipole * 3.33e-30

        # microtubule diffusion constant:
        self.D = p.D_mtube

        # initial angle of microtubules:
        self.mt_theta = np.arctan2(cells.mem_vects_flat[:,3], cells.mem_vects_flat[:,2])

        # normalized microtubule vectors from the cell centre point:
        self.mtubes_x = cells.mem_vects_flat[:,2]
        self.mtubes_y = cells.mem_vects_flat[:,3]

        # microtubule density function initialized:
        mtdx = np.dot(cells.M_sum_mems, self.mtubes_x*cells.mem_sa) / cells.cell_sa
        mtdy = np.dot(cells.M_sum_mems, self.mtubes_y*cells.mem_sa) / cells.cell_sa

        self.mtdf = ((mtdx[cells.mem_to_cells]*cells.mem_vects_flat[:,2] +
                                         mtdy[cells.mem_to_cells]*cells.mem_vects_flat[:,3]))

        self.modulator = np.ones(sim.mdl)  # initialize a modulator structure for the microtubule dynamics

        # Initialize microtubules with mini-simulation to define initial state

        gXo = np.zeros(sim.cdl)
        gYo = np.zeros(sim.cdl)

        if p.init_mtx != 'None' and p.init_mtx is not None:
            Ixo, _ = getattr(mods, p.init_mtx)(cells.cell_i, cells, p)

            gXo = -(Ixo / Ixo.max())

            gX = gXo[cells.mem_to_cells]

        else:
            p.init_mtx = None
            gX = gXo[cells.mem_to_cells]

        if p.init_mty != 'None' and p.init_mty is not None:
            Iyo, _ = getattr(mods, p.init_mty)(cells.cell_i, cells, p)

            gYo = -(Iyo / Iyo.max())

            gY = gYo[cells.mem_to_cells]

        else:
            p.init_mty = None
            gY = gYo[cells.mem_to_cells]

        if p.init_mtx is not None or p.init_mty is not None:

            logs.log_info("Running initialization sequence for microtubules...")

            for tt in range(0, 300):
                # cross-product with director
                Fmt = (self.mtubes_x*gY - self.mtubes_y*gX)/(2*np.pi)

                # calculate rotational flux of microtubule:
                gc_mtdf = np.dot(cells.gradTheta, self.mtdf)

                flux_theta = Fmt - gc_mtdf*1.0e-8
                # flux_theta = Fmt

                self.mt_theta +=  flux_theta*0.15

                # recalculate the new cell microtubule density function:
                mtdx = np.dot(cells.M_sum_mems, self.mtubes_x * cells.mem_sa) / cells.cell_sa
                mtdy = np.dot(cells.M_sum_mems, self.mtubes_y * cells.mem_sa) / cells.cell_sa

                self.mtdf = (mtdx[cells.mem_to_cells] * cells.mem_vects_flat[:, 2] +
                        mtdy[cells.mem_to_cells] * cells.mem_vects_flat[:, 3])

                self.mtubes_x = np.cos(self.mt_theta)
                self.mtubes_y = np.sin(self.mt_theta)

    def reinit(self, cells, p):

        """
        Reinitialize key microtubule parameters that may have changed in config file since init.

        """

        # microtubule diffusion constant:
        self.D = p.D_mtube
        self.visc = p.cytoplasm_viscocity  # viscocity of cytoplasm
        self.charge_mtube = self.tubulin_N*p.tubulin_charge*p.q  # charge on the microtubule
        # microtubule dipole moment [C m] (assumed to be sum of tubulin dimer dipole moments, which are 1740 D each):
        self.p_mtube = self.tubulin_N * p.tubulin_dipole * 3.33e-30

    def update_mtubes(self, cells, sim, p):

        # Force on microtubule due to net charge:
        Fqx = self.charge_mtube*sim.E_cell_x[cells.mem_to_cells]
        Fqy = self.charge_mtube*sim.E_cell_y[cells.mem_to_cells]

        # Torque on microtubule due to net charge 'q':
        if p.microtubules_orient_parallel is True:

            Tq = (self.mtubes_x*Fqy - self.mtubes_y*Fqx)*cells.R_rads

        else:
            Tq = (self.mtubes_x*Fqx + self.mtubes_y*Fqy)*cells.R_rads

        # Torque on microtubule due to dipole component 'p':
        Tp = (self.p_mtube*self.mtubes_x*sim.E_cell_y[cells.mem_to_cells] -
                  self.p_mtube*self.mtubes_y*sim.E_cell_x[cells.mem_to_cells])

        # Drag force torque on microtubule:
        alpha_drag = (p.kb*p.T)

        # calculate rotational flux of microtubule:
        gc_mtdf = np.dot(cells.gradTheta, self.mtdf)

        # angular velocity flux of microtubule:
        flux_theta = -(self.D*gc_mtdf)/(cells.R_rads) + ((Tq + Tp)/alpha_drag)
        # flux_theta = ((Tq + Tp)/alpha_drag)

        self.mt_theta = self.mt_theta + flux_theta*p.dt*self.modulator

        # update the microtubule coordinates with the new angle:
        self.mtubes_x = np.cos(self.mt_theta)
        self.mtubes_y = np.sin(self.mt_theta)

        # recalculate the new cell microtubule density function:
        mtdx = np.dot(cells.M_sum_mems, self.mtubes_x*cells.mem_sa) / cells.cell_sa
        mtdy = np.dot(cells.M_sum_mems, self.mtubes_y*cells.mem_sa) / cells.cell_sa

        self.mtdf = (mtdx[cells.mem_to_cells]*cells.mem_vects_flat[:,2] +
                     mtdy[cells.mem_to_cells]*cells.mem_vects_flat[:, 3])

    def mtubes_to_cell(self, cells, p):

        # determine the microtubules base electroosmotic velocity:
        uxmto = self.mtubes_x
        uymto = self.mtubes_y

        uxmt = np.dot(cells.M_sum_mems, uxmto*cells.mem_sa)/cells.cell_sa
        uymt = np.dot(cells.M_sum_mems, uymto*cells.mem_sa)/cells.cell_sa

        return uxmt, uymt

    def remove_mtubes(self, target_inds_mem, target_inds_cell, cells, sim, p):


        mtubesx2 = np.delete(self.mtubes_x, target_inds_mem)
        self.mtubes_x = mtubesx2*1

        mtubesy2 = np.delete(self.mtubes_y, target_inds_mem)
        self.mtubes_y = mtubesy2*1

        mtdf2 = np.delete(self.mtdf, target_inds_mem)
        self.mtdf = mtdf2*1

        th2 = np.delete(self.mt_theta, target_inds_mem)
        self.mt_theta = th2*1

        mod2 = np.delete(self.modulator, target_inds_mem)
        self.modulator = mod2*1


#-----WASTELANDS
    # def update_mtubes_1(self, cells, sim, p):
    #
    #     cav = 1.0  # concentration at cell centre
    #     cpi = self.cp  # concentration at membrane
    #     z = self.z  # charge of ion
    #     Do = self.D  # diffusion constant of ion
    #
    #     cap = (cav + cpi) / 2  # concentration at midpoint between cell centre and membrane
    #     cgp = (cpi - cav) / cells.R_rads  # concentration gradients
    #
    #     cfluxpo = -Do*cgp + ((Do * p.q * cap * z)/(p.kb * sim.T))*sim.Ec
    #
    #     # as no net mass must leave this intracellular movement, make the flux divergence-free:
    #     cfluxp = stb.single_cell_div_free(cfluxpo, cells)
    #
    #     # calculate the actual concentration at membranes by unpacking to concentration vectors:
    #     self.cp = cpi + cfluxp*(cells.mem_sa/cells.mem_vol)*p.dt
    #
    #     # smooth the concentration:
    #     # self.cp = sim.smooth_weight_mem*self.cp + sim.smooth_weight_o*cav
    #
    #
    #     #-----calculate a "negative end" concentration that has equal and opposite value of z:
    #     can = (1.0 + self.cn) / 2  # concentration at midpoint between cell centre and membrane
    #     cgn = (self.cn - 1.0) / cells.R_rads  # concentration gradients
    #
    #     cfluxno = -Do*cgn - ((Do * p.q * can * z)/(p.kb * sim.T))*sim.Ec
    #
    #     # as no net mass must leave this intracellular movement, make the flux divergence-free:
    #     cfluxn = stb.single_cell_div_free(cfluxno, cells)
    #
    #     # calculate the actual concentration at membranes by unpacking to concentration vectors:
    #     self.cn = self.cn + cfluxn*(cells.mem_sa/cells.mem_vol)*p.dt
    #
    #     # smooth the concentration:
    #     # self.cn = sim.smooth_weight_mem*self.cn + sim.smooth_weight_o*cav
    #
    #     # deal with the fact that our coarse diffusion model may leave some sub-zero concentrations:
    #     indsZ = (self.cp < 0.0).nonzero()
    #
    #     if len(indsZ[0]):
    #         raise BetseSimInstabilityException(
    #             "A microtubule calculation has lead to simulation instability.")
    #
    #     # define microtubule direction vectors in terms of density difference between plus and central minus end:
    #     # component normal to the membrane:
    #
    #     mtno = (self.cp - self.cn)*self.sensitivity
    #
    #     mtx = np.dot(cells.M_sum_mems, mtno*cells.mem_vects_flat[:, 2]*cells.mem_sa) / cells.cell_sa
    #     mty = np.dot(cells.M_sum_mems, mtno*cells.mem_vects_flat[:, 3]*cells.mem_sa) / cells.cell_sa
    #
    #     self.mtubes_xo = cells.mem_vects_flat[:, 2] + mtx[cells.mem_to_cells]
    #     self.mtubes_yo = cells.mem_vects_flat[:, 3] + mty[cells.mem_to_cells]
    #
    #     mtmag = np.sqrt(sim.mtubes.mtubes_xo ** 2 + sim.mtubes.mtubes_yo ** 2)
    #
    #     mtmag[mtmag == 0.0] = 1.0
    #
    #     # normalized microtubule vectors from the cell centre point:
    #     self.mtubes_x = self.mtubes_xo / mtmag
    #     self.mtubes_y = self.mtubes_yo / mtmag


