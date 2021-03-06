import argparse
import atomsmm
import pandas as pd

import math
import random

from sys import stdout
from simtk import openmm
from simtk import unit
from simtk.openmm import app

parser = argparse.ArgumentParser()
parser.add_argument('--timestep', dest='timestep', help='time step size', type=int, required=True)
parser.add_argument('--nsteps', dest='nsteps', help='number of steps', type=int, required=True)
parser.add_argument('--L', dest='L', help='the L parameter', type=int, default=1)
parser.add_argument('--device', dest='device', help='the GPU device', default='None')
parser.add_argument('--secdev', dest='secdev', help='the secondary GPU device', default='None')
parser.add_argument('--seed', dest='seed', help='the RNG seed', type=int, default=0)
parser.add_argument('--platform', dest='platform', help='the computation platform', default='CUDA')
args = parser.parse_args()

seed = random.SystemRandom().randint(0, 2**31) if args.seed == 0 else args.seed
print(f'Employed RNG seed is {seed}')

base = f'dt{args.timestep:02d}fs-L{args.L}'
platform_name = args.platform

dt = args.timestep*unit.femtoseconds
temp = 298.15*unit.kelvin
rcut = 12*unit.angstroms
rswitch = 11*unit.angstroms
rcutIn = 8*unit.angstroms
rswitchIn = 5*unit.angstroms
tau = 10*unit.femtoseconds
gamma = 0.1/unit.femtoseconds
reportInterval = 90//args.timestep

platform = openmm.Platform.getPlatformByName(platform_name)
properties = dict(Precision='mixed') if platform_name == 'CUDA' else dict()
if args.device != 'None':
    properties['DeviceIndex'] = args.device

pdb = app.PDBFile('water.pdb')
forcefield = app.ForceField('water.xml')
openmm_system = forcefield.createSystem(pdb.topology,
                                        nonbondedMethod=openmm.app.PME,
                                        nonbondedCutoff=rcut,
                                        rigidWater=False,
                                        removeCMMotion=False)

nbforce = openmm_system.getForce(atomsmm.findNonbondedForce(openmm_system))
nbforce.setUseSwitchingFunction(True)
nbforce.setSwitchingDistance(rswitch)
nbforce.setUseDispersionCorrection(False)

if args.timestep > 3:
    respa_system = atomsmm.RESPASystem(openmm_system, rcutIn, rswitchIn, fastExceptions=False)
    loops = [6, args.timestep//3, 1]
else:
    respa_system = openmm_system
    for force in respa_system.getForces():
        if isinstance(force, openmm.NonbondedForce):
            force.setReciprocalSpaceForceGroup(1)
            force.setForceGroup(1)
    loops = [2*args.timestep, 1]

#integrator = atomsmm.integrators.LimitedSpeedStochasticVelocityIntegrator(dt, loops, temp, tau, gamma, L=args.L)
integrator = atomsmm.integrators.LimitedSpeedStochasticIntegrator(dt, loops, temp, tau, gamma, L=args.L)

simulation = openmm.app.Simulation(pdb.topology, respa_system, integrator, platform, properties)
simulation.context.setPositions(pdb.positions)
simulation.context.setVelocitiesToTemperature(temp, seed)

computer = atomsmm.PressureComputer(openmm_system,
        pdb.topology,
        openmm.Platform.getPlatformByName('CPU'),
#        dict(Precision='mixed', DeviceIndex=args.secdev),
        temperature=temp)

dataReporter = atomsmm.ExtendedStateDataReporter(stdout, reportInterval, separator=',',
        step=True,
        potentialEnergy=True,
        temperature=True,
#        atomicPressure=True,
#        molecularPressure=True,
#        pressureComputer=computer,
        speed=True,
        extraFile=f'{base}.csv')

simulation.reporters += [dataReporter]
simulation.step(args.nsteps)
