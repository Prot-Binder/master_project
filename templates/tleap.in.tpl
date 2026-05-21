#Load the Force Field;
source {FORCEFIELD_DIR}/leaprc.cyclic.ff14SB
loadamberparams frcmod.ionsjc_tip3p
source leaprc.water.tip3p

#Load the PDB
mol=loadpdb {PDB_PATH}

#Head to tail peptide bond
{BOND}

#solvate the structure
solvateoct mol TIP3PBOX 20

#Add ions for right salt concentration 2842014.733  A^3 * 0.00009 = 255.78
addionsRand mol Na+ 256 Cl- 256
addIonsRand mol Na+ {N_NA}
addIonsRand mol Cl- {N_CL}


#Check & LOADOFF the topology and coordinate files
check mol
savepdb mol system.pdb
saveamberparm mol system.prmtop system.rst

quit

