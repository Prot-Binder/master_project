path to this github repository:

potential error: currently, we use absolut paths to specify the DISANG etc. file locations. If the filepaths are too long (probably > 80 characters), AMBER might throw and error that the file could not be opened. So shorten the filepath or ajdust it to relative filepaths.

We have some dependencies, that are reasonable, e.g. eq should run at first for every system and flag. Hence, if eq is not specified, 
the code expects that eq files exist, e.g. restrt4 exists. If this file exists, but eq is still running, this is not considered.

remember to load ambertools so that tleap is availabe on the cluster.

pull:
we can specify nstlim; the first 100,000 steps are used to pull the system with a lower force constant: from k/2 to k. 

rs-remd:
setup (e.g. restraint file for pulling to equilibrium distance and _lroaus restraints) can only be created once the eq.
was performed as the eq. distance is needed to create the restraint file for the pulling step and the _lroaus restraints.
So first perform the eq. and then create the setup for rs-remd.