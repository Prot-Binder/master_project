#!/usr/bin/env bash

tleap_path=$1

#run tleap
tleap -f ${tleap_patht}leap.in

python3 calc_ions.py

tleap -f ${tleap_patht}tleap.in

parmed -i ${tleap_patht}HMR.parmed
