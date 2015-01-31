#!/usr/bin/env python3
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

import pickle


def saveSim(savePath,datadump):
    with open(savePath, 'wb') as f:
        pickle.dump(datadump, f)

def loadSim(loadPath):

    with open(loadPath, 'rb') as f:
        sim,cells,p = pickle.load(f)

    return sim,cells,p

def loadWorld(loadPath):

    with open(loadPath, 'rb') as f:
        cells = pickle.load(f)

    return cells