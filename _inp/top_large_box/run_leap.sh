#!/usr/bin/env bash

#run tleap
tleap -f tleap.in

python3 calc_ions.py

tleap -f tleap.in

#cp prmtop and rst file
cp system_wb* ../
