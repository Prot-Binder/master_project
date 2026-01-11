from __future__ import division
import sys
import os
from math import sqrt
import subprocess
import argparse
import numpy as np
from pathlib import Path
import parmed as pmd
import parmed.tools as t
from parmed.amber import AmberMask


def mask_from_atoms(atoms):
    return "@" + ",".join(map(lambda a: str(a.idx + 1), atoms))


def group_by(atoms, keyfunc):
    """
    Return a dictionary with the following format: {keyfunc(atom): [atoms]}, where the
    atoms are grouped by the return value of keyfunc(atom).
    """
    groups = {}
    for atom in atoms:
        key = keyfunc(atom)
        group = groups.setdefault(key, [])
        group.append(atom)
    return groups


def group_by_ljtype(parm, mask):
    """Group atoms in mask by LJ type index."""
    atoms = parm.view[mask]
    groups = group_by(atoms, lambda atom: atom.nb_idx)
    return groups


def add_lj_types(parm, not_ligand_groups, ligand_groups):
    """
    Add new LJ type for every atom type in the ligand, so that the ligand has no LJ type
    in common with the rest.
    """
    assert len(ligand_groups) > 0

    for nb_idx, atoms in ligand_groups.items():
        if not nb_idx in not_ligand_groups:
            # don't create a new type when we don't need to i.e. when this type only
            # appears in the ligand; T: wenn Bedingung erfuellt macht keinen neuen lj type
            continue
        t.addLJType(parm, mask_from_atoms(atoms)).execute()


def change_lj_pairs(parm, receptor_groups, ligand_groups, interaction_func):
    """
    Change LJ pair interaction parameters between receptor and ligand.
    interaction_func(atom1, atom2):
        a function that returns the new interaction parameters (rmin, epsilon)
    """
    assert len(ligand_groups) > 0 and len(receptor_groups) > 0

    for group_r in receptor_groups.values():
        for group_l in ligand_groups.values():
            # enough to look at first atom (only nb_idx is relevant)
            rmin, epsilon = interaction_func(group_r[0], group_l[0])

            mask_r = "@" + str(group_r[0].idx + 1)
            mask_l = "@" + str(group_l[0].idx + 1)

            t.changeLJPair(parm, mask_r, mask_l, rmin, epsilon).execute()


class InterpolateBase(object):
    def __init__(self, strength, **kwargs):
        self.strength = strength

    method = "no interpolation"

    def __call__(self, atom1, atom2):
        rmin = atom1.rmin + atom2.rmin
        epsilon = sqrt(atom1.epsilon * atom2.epsilon)
        return rmin, epsilon


class InterpolateVolumeScaling(InterpolateBase):
    method = "volume scaling of e"

    def __init__(self, strength, interpolator_prev, d_max, e_min, d_fixed, e_fixed, **kwargs):
        if d_fixed:
            self.d = d_max
        else:
            self.d = strength * d_max
        if e_fixed:
            self.e = e_min
        else:
            self.e = interpolate_lin(1, e_min, strength)

    def __call__(self, atom1, atom2):
        # sometimes happens between two H atoms for example
        if atom1.rmin + atom2.rmin == 0.0:
            return 0.0, 0.0

        new_rmin = (atom1.rmin + atom2.rmin) + self.d

        e_scaling = (atom1.rmin + atom2.rmin) ** 3 / new_rmin ** 3
        epsilon = sqrt(atom1.epsilon * atom2.epsilon) * e_scaling * self.e

        return new_rmin, epsilon


def interpolate_lin(a, b, fraction):
    return a + (b - a) * fraction


def HMassRepartition(parm):
    t.HMassRepartition(parm).execute()

    return parm


def write_topology(parm, output_file, n=None):
    filename = output_file
    if n != None:
        #        filename = filename.replace(".top", "_{}.top".format(n+1))
        filename = filename + "{}".format(n + 1)
    parm.write_parm(filename)
    with open(filename + ".txt", "w") as f:
        f.write(str(t.printLJMatrix(parm, "*")))

def generate_scaled_top_files(topology_file: Path, num_replicas: int, distances: list[float],
                         epsilons: list[float], coordinate_file: Path, output_file_basename: Path,
                         protein_mask: str, ligand_mask: str, d_fixed: bool = False,
                         e_fixed: bool = False, hMassRepartitioning: bool = True) -> None:

    not_ligand_mask = "!" + ligand_mask

    interpolation_methods = [InterpolateVolumeScaling]
    Method = interpolation_methods[0]

    ds = distances
    es = epsilons
    assert (len(ds) == 1 or len(ds) == num_replicas)
    assert (len(es) == 1 or len(es) == num_replicas)
    if len(ds) > 1:
        d_fixed = True
    if len(es) > 1:
        e_fixed = True

    # load parameter and possibly coordinate file
    print('Scaling based on the following files:')
    # Ensure paths are resolved and exist
    topology_file = topology_file.resolve()
    coordinate_file = coordinate_file.resolve()

    if not topology_file.exists():
        raise FileNotFoundError(f"Topology file not found: {topology_file}")
    if not coordinate_file.exists():
        raise FileNotFoundError(f"Coordinate file not found: {coordinate_file}")

    # parm = pmd.amber.AmberParm(topology_file, xyz=coordinate_file)
    print(topology_file)
    print(coordinate_file)
    parm = pmd.amber.AmberParm(str(topology_file), xyz=str(coordinate_file))

    # change the lj types
    protein_groups = group_by_ljtype(parm, protein_mask)
    ligand_groups = group_by_ljtype(parm, ligand_mask)
    not_ligand_groups = group_by_ljtype(parm, not_ligand_mask)
    add_lj_types(parm, not_ligand_groups, ligand_groups)

    # go through each replica and change lj parameters
    interpolator_prev = None
    parms = []
    orig_charge = parm.parm_data['CHARGE']
    for n, fraction in enumerate(np.linspace(0, 1, num_replicas)):
        d = ds[n] if len(ds) > 1 else ds[0]
        e = es[n] if len(es) > 1 else es[0]

        interpolator = Method(fraction, interpolator_prev=interpolator_prev,
                              d_max=d, e_min=e,
                              d_fixed=d_fixed, e_fixed=e_fixed)
        interpolator_prev = interpolator
        # change lj parameters
        change_lj_pairs(parm, protein_groups, ligand_groups, interpolator)
        if hMassRepartitioning is not None:
            HMassRepartition(parm)
        write_topology(parm, str(output_file_basename), n)
