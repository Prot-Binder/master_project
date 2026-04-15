import re
import varname
import argparse
import warnings
import numpy as np
from pathlib import Path
import MDAnalysis as mda
from matplotlib import pyplot as plt
from MDAnalysis.lib.distances import calc_angles
from MDAnalysis.lib.distances import calc_dihedrals
from MDAnalysis.topology.guessers import guess_types

class ARW_setup(mda.core.universe.Universe):
    
    def __init__(self, 
                 topfile,
                 receptor,
                 ligand,
                 krec=10.0,
                 klig=10.0,
                 kTheta=100.0,
                 kPhi=100.0,
                 kPsi=100.0,
                 ktheta=100.0,
                 kphi=100.0,
                 kdist=2.0,
                 userSpecifiedTheta0=None,
                 userSpecifiedPhi0=None,
                 userSpecifiedPsi0=None,
                 userSpecifiedtheta0=None,
                 userSpecifiedphi0=None,
                 userSpecifiedRMSDlig=0.0,
                 userSpecifiedRMSDrec=0.0):
        
        super(ARW_setup, self).__init__(topfile)
        self.guess_missing_attr()
        self.topfile = topfile
        self.receptor = receptor
        self.ligand = ligand
        self.rec = self.select_atoms(self.receptor)
        self.lig = self.select_atoms(self.ligand)
        self.krec = krec
        self.klig = klig
        self.kTheta = kTheta
        self.kPhi = kPhi
        self.kPsi = kPsi
        self.ktheta = ktheta
        self.kphi = kphi
        self.kdist = kdist
        self.userSpecifiedRMSDlig = userSpecifiedRMSDlig
        self.userSpecifiedRMSDrec = userSpecifiedRMSDrec
        self.userSpecifiedTheta0 = userSpecifiedTheta0
        self.userSpecifiedPhi0 = userSpecifiedPhi0
        self.userSpecifiedPsi0 = userSpecifiedPsi0
        self.userSpecifiedtheta0 = userSpecifiedtheta0
        self.userSpecifiedphi0 = userSpecifiedphi0    
    
    def guess_missing_attr(self):
        if hasattr(self.atoms,'elements'):
            return()
        else: 
            guessed_elements = guess_types(self.atoms.names)
            self.add_TopologyAttr('elements', guessed_elements)
            warnings.warn('Topology does not contain element information, so they will be \
                           guessed by MDAnalysis. Proceed with caution.')
            
    def calc_rgyr(self, attr):
        ag = getattr(self, attr)
        # get squared distance from center
        ri = ag.positions - ag.center_of_mass()
        # total mass calculation for the predefined atomgroup
        totmass = np.sum(ag.masses)
        # weight positions
        r_gyr = np.sqrt(np.sum(ag.masses*np.linalg.norm(ri, axis=1)**2)/totmass)
        # square root and return
        return r_gyr
        
    def find_anchor_groups(self, attr):
        
        ag = getattr(self,attr)
        com = ag.center_of_mass()
        # Calculate the radius of gyration; heuristic to find suitable atom anchors
        r_gyr = self.calc_rgyr(attr)
        f_rgyr = np.floor(r_gyr)
        c_rgyr = np.ceil(r_gyr)

        # define the COM position as a string for inputting it into the atom selection with a rgyr-dist criterion
        com_str = " ".join(ag.center_of_mass().astype(str))
        ag_rgyr = ag.select_atoms('point {} {} and not point {} {}'.format(com_str, c_rgyr, com_str, f_rgyr))
        
        # get indices of most orthogonal atoms of the ag_rgyr
        orthoi, orthoj, ortho = 0,0,100
        for i,ag1 in enumerate(ag_rgyr):
            for j,ag2 in enumerate(ag_rgyr): 
                angle = calc_angles(ag1.residue.atoms.center_of_mass(),com,ag2.residue.atoms.center_of_mass())
                if abs(angle - 0.5*np.pi) < ortho:
                    ortho = abs(angle - 0.5*np.pi)
                    orthoi,orthoj = i,j
        # save the residues of said atoms in an atom group and return them
        ag_com1 = ag_rgyr[orthoi].residue.atoms
        ag_com2 = ag_rgyr[orthoj].residue.atoms
        return(ag_com1,ag_com2)
    
    def set_anchors(self):
        for attr in ['rec','lig']:
            try:
                ag0 = getattr(self, attr)
                ag1, ag2 = self.find_anchor_groups(attr)
                ag_com0 = ag0.center_of_mass()
                ag_com1 = ag1.center_of_mass()
                ag_com2 = ag2.center_of_mass()
                ag_anchor = {'0': ag0,
                             '1': ag1,
                             '2': ag2,
                             'com0': ag_com0,
                             'com1': ag_com1,
                             'com2': ag_com2,
                            }
                setattr(self, attr+'_anchor', ag_anchor)
            except ValueError:
                warnings.warn('self.{} is not defined and no anchors could be set. Ignore \
                               this message if this is intentional for the bulk simulations.'.format(attr)) 
        
        
    def save_anchor_view(self, anchorsPDB='anchors.pdb', ligrecPDB='lig_rec.pdb'):
        u_anchor = mda.Universe.empty(n_atoms = 6,
                         n_residues = 6,
                         atom_resindex = [0,1,2,3,4,5],
                         residue_segindex = [0]*6,
                         trajectory = True)
        
        u_anchor.add_TopologyAttr('name', ['lig0', 'lig1', 'lig2','rec0', 'rec1', 'rec2'])
        u_anchor.add_TopologyAttr('type', ['Dummy', 'Dummy', 'Dummy','Dummy', 'Dummy', 'Dummy'])
        u_anchor.add_TopologyAttr('resname', ['lig0', 'lig1', 'lig2','rec0', 'rec1', 'rec2'])
        u_anchor.add_TopologyAttr('segid', ['DUM'])
        u_anchor.add_TopologyAttr('chainID', ['A']*6)
        
        u_anchor.select_atoms('name lig0').positions = self.lig_anchor['com0']
        u_anchor.select_atoms('name lig1').positions = self.lig_anchor['com1']
        u_anchor.select_atoms('name lig2').positions = self.lig_anchor['com2']
        u_anchor.select_atoms('name rec0').positions = self.rec_anchor['com0']
        u_anchor.select_atoms('name rec1').positions = self.rec_anchor['com1']
        u_anchor.select_atoms('name rec2').positions = self.rec_anchor['com2']
        u_anchor.atoms.write(anchorsPDB)
        
        self.select_atoms('not (resname WAT or resname Na+ or resname Cl-)').write(ligrecPDB)
        
        
    def parameterise_MULTI_RMSD(self, attr):
        anchor = getattr(self,attr+'_anchor')
        cv_i =','.join(anchor['0'].ids.astype(str))
        cv_r =','.join(anchor['0'].positions.reshape(-1).astype(str))
        cv_ni = anchor['0'].n_atoms
        cv_nr = anchor['0'].n_atoms*3
        return cv_i, cv_r, cv_ni, cv_nr
    
    
    def parameterise_COM_ANGLE(self,ag0,ag1,ag2):
        ''' Is supposed to generate amber cv_in strings for the following angle:
              1---2    
             /angle
            0
        '''
        com0 = ag0.center_of_mass()
        com1 = ag1.center_of_mass()
        com2 = ag2.center_of_mass()

        # MDA function to calculate angle of three positions
        angle = np.round(calc_angles(com0,com1,com2),3)
        # 300 kcal/mol/radian**2 = 0.1 kcal/mol/degree**2 from chipot et roux; seems pretty high though
        # 3 because of the three 0's that are part of the cv_i statement
        angle_ni = 3 + ag0.n_atoms + ag1.n_atoms + ag2.n_atoms
        angle_i0 = ",".join(ag0.ids.astype(str))
        angle_i1 = ",".join(ag1.ids.astype(str))
        angle_i2 = ",".join(ag2.ids.astype(str))
        return angle,angle_ni,angle_i0,angle_i1,angle_i2

    
    def parameterise_COM_TORSION(self, ag0, ag1, ag2, ag3):
        ''' Is supposed to generate amber cv_in strings for the following dihedral:
                  2---3
                 /dihdrl
            0---1
        '''
        # define center of masses from the atom groups 
        # (they are already known to the class, but code wise this is just cleater)
        com0 = ag0.center_of_mass()
        com1 = ag1.center_of_mass()
        com2 = ag2.center_of_mass()
        com3 = ag3.center_of_mass()

        # MDA function to calculate the dihedral between 4 coordinates
        tors = np.round(calc_dihedrals(com0, com1, com2, com3),3)
        
        # 4 because of the three 0's that are part of the cv_i statement
        tors_ni = (4 + ag0.n_atoms 
                     + ag1.n_atoms
                     + ag2.n_atoms 
                     + ag3.n_atoms)
        tors_i0 = ",".join(ag0.ids.astype(str))
        tors_i1 = ",".join(ag1.ids.astype(str))
        tors_i2 = ",".join(ag2.ids.astype(str))
        tors_i3 = ",".join(ag3.ids.astype(str))
        # output the torsion parameters for further use (e.g. by write_COM_TORSION method)
        return tors, tors_ni, tors_i0, tors_i1, tors_i2, tors_i3
    
    def write_MULTI_RMSD(self, attr, file, k_rmsd=0, referenceRMSD=1.0):
        
        if referenceRMSD == None: referenceRMSD=1.0 
        lowerRMSD = np.round(referenceRMSD - 15, 3)
        upperRMSD = np.round(referenceRMSD + 15, 3)
        
        cv_i, cv_r, cv_ni, cv_nr = self.parameterise_MULTI_RMSD(attr)
        file.write('&colvar ! {} RMSD Restraints\n'.format(attr.upper()))
        file.write("\tcv_type = 'MULTI_RMSD'\n")
        file.write('\tcv_ni = {}, cv_nr = {},\n'.format(cv_ni, cv_nr))
        file.write('\tcv_i = {},\n'.format(cv_i))
        file.write('\tcv_r = {},\n'.format(cv_r))
        file.write('\tanchor_position = {}, {}, {}, {},\n'.format(lowerRMSD,referenceRMSD,referenceRMSD,upperRMSD))
        file.write('\tanchor_strength = {}, {},/\n'.format(k_rmsd,k_rmsd))
        
    def write_COM_ANGLE(self, file, ang_name, k_ang=0):
        if ang_name == 'Theta': 
            ang_type = 'Theta Orientational Restraints'
            ang, ang_ni, ang_i0, ang_i1, ang_i2 = self.parameterise_COM_ANGLE(self.lig_anchor['1'],
                                                                              self.lig_anchor['0'],
                                                                              self.rec_anchor['0'])
            if self.userSpecifiedTheta0: ang = self.userSpecifiedTheta0
        elif ang_name == 'theta': 
            ang_type = 'theta Spherical Restraints'
            ang, ang_ni, ang_i0, ang_i1, ang_i2 = self.parameterise_COM_ANGLE(self.rec_anchor['1'],
                                                                              self.rec_anchor['0'],
                                                                              self.lig_anchor['0'])
            if self.userSpecifiedtheta0: ang = self.userSpecifiedtheta0
        else:
            raise ValueError('{} isnt a valid option for ang_name. Either use "Theta" for ori., angular restraints or "theta" for sph., angular restraints.'.format(ang_name))
            
        low = np.round(ang-1.5,3)
        up = np.round(ang+1.5,3)

        file.write('&colvar ! {}\n'.format(ang_type))
        file.write("\tcv_type = 'COM_ANGLE'\n")
        file.write('\tcv_ni = {},\n'.format(ang_ni))
        file.write('\tcv_i = {},0,{},0,{},0,\n'.format(ang_i0, ang_i1, ang_i2))
        file.write('\tanchor_position = {}, {}, {}, {},\n'.format(low, ang, ang, up))
        file.write('\tanchor_strength = {}, {},/\n'.format(k_ang,k_ang))
        
    def write_COM_TORSION(self, file, tors_name, k_tors=0):
        # if else clauses to distinguish between the different torsions necessary for woo roux method
        if tors_name == 'Phi': 
            tors_type = 'Phi Orientational Restraints'
            tors, tors_ni, tors_i0, tors_i1, tors_i2, tors_i3 = self.parameterise_COM_TORSION(self.rec_anchor['0'],
                                                                                              self.lig_anchor['0'],
                                                                                              self.lig_anchor['1'],
                                                                                              self.lig_anchor['2'])
            if self.userSpecifiedPhi0: tors = self.userSpecifiedPhi0
            
        elif tors_name == 'Psi': 
            tors_type = 'Psi Orientational Restraints'
            tors, tors_ni, tors_i0, tors_i1, tors_i2, tors_i3 = self.parameterise_COM_TORSION(self.rec_anchor['1'],
                                                                                              self.rec_anchor['0'],
                                                                                              self.lig_anchor['0'],
                                                                                              self.lig_anchor['1'])
            if self.userSpecifiedPsi0: tors = self.userSpecifiedPsi0
            
        elif tors_name == 'phi': 
            tors_type = 'phi Spherical Restraints'
            tors, tors_ni, tors_i0, tors_i1, tors_i2, tors_i3 = self.parameterise_COM_TORSION(self.rec_anchor['2'],
                                                                                              self.rec_anchor['1'],
                                                                                              self.rec_anchor['0'],
                                                                                              self.lig_anchor['0'])
            if self.userSpecifiedphi0: tors = self.userSpecifiedphi0
        else:
            raise ValueError('{} isnt a valid option for torsname. Either use "Phi"/"Psi" for ori., angular restraints or "phi" for sph., angular restraints.'.format(tors_name))
            
        low = np.round(tors-1.5,3)
        up = np.round(tors+1.5,3)

        file.write('&colvar ! {}\n'.format(tors_type))
        file.write("\tcv_type = 'COM_TORSION'\n")
        file.write('\tcv_ni = {},\n'.format(tors_ni))
        file.write('\tcv_i = {},0,{},0,{},0,{},0,\n'.format(tors_i0, tors_i1, tors_i2, tors_i3))
        file.write('\tanchor_position = {}, {}, {}, {},\n'.format(low, tors, tors, up))
        file.write('\tanchor_strength = {}, {},/\n'.format(k_tors,k_tors))
    
    
    def write_COM_DIST(self, file, k_dist=0):
        
        com_ni = self.lig_anchor['0'].n_atoms + self.rec_anchor['0'].n_atoms
        com_i0 = ','.join(self.lig_anchor['0'].ids.astype(str))
        com_i1 = ','.join(self.rec_anchor['0'].ids.astype(str))
        
        file.write('&colvar ! R_COM between Ligand and Receptor\n')
        file.write("\tcv_type = 'COM_DISTANCE'\n")
        file.write('\tcv_ni = {},\n'.format(com_ni))
        file.write('\tcv_i = {},0,{},0\n'.format(com_i0, com_i1))
        # file.write('\tanchor_position = {}, {}, {}, {},\n'.format(0, 'WINDOW', 'WINDOW', 99))
        # file.write('\tanchor_strength = {}, {},/\n'.format(k_dist, k_dist))
        file.write('\tanchor_position = {}, {}, {}, {},\n'.format(0, '{WINDOW}', '{WINDOW}', 99))
        file.write('\tanchor_strength = {}, {},/\n'.format("{KAPPA}", "{KAPPA}"))


    def write_pull_file(self, filename, initial_distance=None, final_distance=None,
                   pull_steps=100000, initial_force=None, final_force=None, increment_freq=100):
        """
        Write AMBER pull restraint file for the pulling phase of APR calculations.
        
        Parameters:
        -----------
        filename : str
            Output filename for the pull restraint file
        initial_distance : float
            Starting distance for the pull (default: 8.0 Å)  
        final_distance : float
            Final distance for the pull (if None, uses 'WINDOW' placeholder)
        pull_steps : int
            Number of steps for the pulling phase (default: 100000)
        initial_force : float
            Initial force constant (default: 0.2 kcal/mol/Å²)
        final_force : float
            Final force constant (default: 4.0 kcal/mol/Å²)
        increment_freq : int
            Frequency of force increments (default: 100 steps)
        """
        
        # Get atom IDs for COM calculations
        rec_ids = ','.join(self.rec_anchor['0'].ids.astype(str))
        lig_ids = ','.join(self.lig_anchor['0'].ids.astype(str))
        
        # Set final distance - use WINDOW placeholder if not specified
        # final_dist_str = str(final_distance) if final_distance is not None else 'WINDOW'
        final_dist_str = str(final_distance) if final_distance is not None else '{WINDOW}'
        
        # Calculate number of increments
        ninc = pull_steps // increment_freq

        initial_dist_str = str(f"{initial_distance:.5f}") if initial_distance is not None else '{WINDOW_PREV}'
        initial_force_str = str(f"{initial_force:.3f}") if initial_force is not None else '{KAPPA_INIT}'

        final_force_str = str(f"{final_force:.2f}") if final_force is not None else '{KAPPA}'

        total_steps = "{TOTAL_STEPS}"
        
        with open(filename, 'w') as file:
            # First restraint block - pulling phase
            file.write('&rst\n')
            file.write(f'\tiat=-1,-1, nstep1=1, nstep2={pull_steps}, ifvari=1, ninc={ninc},\t\t ! COM-Restr. /w {ninc}incrmts evry {increment_freq}stps\n')
            file.write(f'\tr1=0.00, r2={initial_dist_str}, r3={initial_dist_str}, r4=99.00, rk2={initial_force_str}, rk3={initial_force_str}, ! nstep1 Anchor Pos+Strngth for harm. pot.\n')
            file.write(f'\tr1a=0.0, r2a={final_dist_str}, r3a={final_dist_str}, r4a=99.0, rk2a={final_force_str}, rk3a={final_force_str}, ! nstep2 Anchor Pos+Strength for harm. pot.\n')
            file.write('\t! Atom IDs for calculation of COM Positions of the Receptor\n')
            file.write(f'\tigr1={rec_ids}\n')
            file.write('\t\n')
            file.write('\t! Atom IDs for calculation of COM Positions of the Ligand\n')
            file.write(f'\tigr2={lig_ids}\n')
            file.write('/\n')
            
            # Second restraint block - equilibration at final distance
            file.write('&rst\n')
            file.write(f'\tiat=-1,-1, nstep1={pull_steps + 1}, nstep2={total_steps}, \t\t           ! const. COM-Restr. from step {pull_steps + 1}\n')
            file.write(f'\tr1=0.0, r2={final_dist_str}, r3={final_dist_str}, r4=99.0, rk2={final_force_str}, rk3={final_force_str}, ! Anchor Pos+Strngth for harm. pot.\n')
            file.write('\t! Atom IDs for calculation of COM Positions of the Receptor\n')
            file.write(f'\tigr1={rec_ids}\n')
            file.write('\t\n')
            file.write('\t! Atom IDs for calculation of COM Positions of the Ligand\n')
            file.write(f'\tigr2={lig_ids}\n')
            file.write('/\n')
    
    def write_restraint_file(self,filename, lig=None, rec=None, ori=None, ang=None, com=None):
        
        with open(filename, 'w') as file:
            match(lig):
                case True : self.write_MULTI_RMSD('lig',file,self.klig, self.userSpecifiedRMSDlig)
                case False: self.write_MULTI_RMSD('lig',file, referenceRMSD=self.userSpecifiedRMSDlig)
                case None : pass

            match(rec):
                case True : self.write_MULTI_RMSD('rec',file, self.krec, self.userSpecifiedRMSDrec)
                case False: self.write_MULTI_RMSD('rec',file, referenceRMSD=self.userSpecifiedRMSDrec)
                case None : pass

            match(ori):
                case True:
                    self.write_COM_ANGLE(file, 'Theta', k_ang=self.kTheta)
                    self.write_COM_TORSION(file, 'Phi', k_tors=self.kPhi)
                    self.write_COM_TORSION(file, 'Psi', k_tors=self.kPsi)
                case False:
                    self.write_COM_ANGLE(file, 'Theta')
                    self.write_COM_TORSION(file, 'Phi')
                    self.write_COM_TORSION(file, 'Psi')
                case None:
                    pass

            match(ang):
                case True:
                    self.write_COM_ANGLE(file, 'theta', k_ang=self.ktheta)
                    self.write_COM_TORSION(file, 'phi', k_tors=self.kphi)
                case False:
                    self.write_COM_ANGLE(file, 'theta')
                    self.write_COM_TORSION(file, 'phi')
                case None:
                    pass

            match(com):
                case  True: self.write_COM_DIST(file,k_dist=self.kdist)
                case False: self.write_COM_DIST(file)
                case  None: pass

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="Path to PDB-file created with tleap.")
    parser.add_argument("-r", "--receptor", help="Indices of residues corresponding to the receptor. Specify range as follows: \"1-123\"")
    parser.add_argument("-l", "--ligand", help="Indices of the residues corresponding to the ligand. Specify range as follows: \"125-130\"")
    
    return parser.parse_args()

def create_restraints(setup_path: Path, pdb_path: Path, protein: str, ligand: str):
    if ('-' not in protein) or ('-' not in ligand):
        raise ValueError("Receptor or ligand interval string is not properly formated. Try to use: \"1-123\"")

    r_start = protein.split('-')[0]
    r_end = protein.split('-')[1]
    l_start = ligand.split('-')[0]
    l_end = ligand.split('-')[1]
    test1 = ARW_setup(pdb_path, receptor=f'resid {r_start} to {r_end} and not element H', ligand=f'resid {l_start} to {l_end} and not element H')

    test1.set_anchors()
    test1.save_anchor_view(anchorsPDB=f'{setup_path}/anchors.pdb', ligrecPDB=f'{setup_path}/lig_rec.pdb')
    test1.write_restraint_file(f"{setup_path}/_.r",False, False, False, False, None) #measure colvars
    test1.write_restraint_file(f"{setup_path}/_l.r",True, False, False, False, None)
    test1.write_restraint_file(f"{setup_path}/_lr.r",True, True, False, False, None)
    test1.write_restraint_file(f"{setup_path}/_lro.r",True, True, True, False, None)
    test1.write_restraint_file(f"{setup_path}/_lroa.r",True, True, True, True, None)
    test1.write_restraint_file(f"{setup_path}/_lroaus.r",True, True, True, True,True)
    test1.write_pull_file(f'{setup_path}/pull.r', final_distance=None)