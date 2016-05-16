#!/usr/bin/env python3
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

import numpy as np


def eosmosis(sim, cells, p):
    """
    Movement of ion pumps and channels to potentially create directional fluxes in individual cells.

    This is presently simulated by calculating the Nernst-Planck concentration flux of a weighting
    agent, rho, which moves under its own concentration gradient (a homogeneity restoring influence)
    as well as under the influence of the extracellular voltage gradient and fluid flows tangential
    to the membrane.

    """

    # x and y components of membrane tangent unit vectors
    tx = cells.mem_vects_flat[:, 4]
    ty = cells.mem_vects_flat[:, 5]

    # tangential components of fluid flow velocity at the membrane, if applicable:
    if p.fluid_flow is True and p.sim_ECM is True:
        # map the flow vectors to membrane midpoints
        ux_mem = sim.u_env_x.ravel()[cells.map_mem2ecm]
        uy_mem = sim.u_env_y.ravel()[cells.map_mem2ecm]

        # tangential component of fluid velocity at membrane:
        u_tang = ux_mem*tx + uy_mem*ty

    else:
        u_tang = 0

    # get the gradient of rho concentration around each membrane:
    grad_c_p =  np.dot(cells.gradMem, sim.rho_pump)
    grad_c_ch = np.dot(cells.gradMem, sim.rho_channel)

    # get the tangential electric field at each membrane
    if p.sim_ECM is True:

        Ex = sim.E_env_x.ravel()[cells.map_mem2ecm]
        Ey = sim.E_env_y.ravel()[cells.map_mem2ecm]

    else:  # if not simulating extracellular spaces, then use the intracellular field instead:
        Ex = sim.E_gj_x
        Ey = sim.E_gj_y

    # get the tangential component to the membrane:
    E_tang = Ex * tx + Ey * ty

    # calculate the total Nernst-Planck flux at each membrane for rho_pump factor:

    flux_pump = -p.D_membrane*grad_c_p + u_tang*sim.rho_pump + \
                ((p.z_pump*p.D_membrane*p.F)/(p.R*p.T))*sim.rho_pump*E_tang

    flux_chan = -p.D_membrane * grad_c_ch + u_tang * sim.rho_channel + \
                ((p.z_channel * p.D_membrane * p.F) / (p.R * p.T)) * sim.rho_channel * E_tang


    # divergence of the total flux:

    divF_pump = np.dot(cells.gradMem,flux_pump)
    divF_chan = np.dot(cells.gradMem, flux_chan)

    sim.rho_pump = sim.rho_pump - divF_pump * p.dt
    sim.rho_channel = sim.rho_channel - divF_chan * p.dt

    # ------------------------------------------------
    # make sure nothing is non-zero:
    fix_inds = (sim.rho_pump < 0).nonzero()
    sim.rho_pump[fix_inds] = 0

    fix_inds2 = (sim.rho_channel < 0).nonzero()
    sim.rho_channel[fix_inds2] = 0