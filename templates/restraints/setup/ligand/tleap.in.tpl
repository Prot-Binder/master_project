#Load the Force Field
source ./leaprc.cyclic.ff14SB
loadamberparams frcmod.ionsjc_tip3p
source leaprc.water.tip3p

#Load the PDB
mol=loadpdb {PDB_PATH}

#Head to tail peptide bond
{BOND}

#solvate the structure
solvateoct mol TIP3PBOX 12.5

#Add ions for right salt concentration
addionsRand mol Na+ 10 Cl- 10
addIonsRand mol Na+ 0
addIonsRand mol Cl- 0


#Check & LOADOFF the topology and coordinate files
check mol
savepdb mol system_wb.pdb
saveamberparm mol system_wb.prmtop system_wb.rst

quit