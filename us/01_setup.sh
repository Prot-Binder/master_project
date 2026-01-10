#!/bin/bash
export LC_NUMERIC=C  # Ensures decimal numbers use a dot instead of a comma
INPDIR="../_inp"
OUTDIR="_output"
TRASH="_trash"
JOBID="mhc"

mkdir -p $OUTDIR $TRASH

copy_input_files()
{
	cp -v $INPDIR/em.in mdin0		# EM with CPU (double precision)
	cp -v $INPDIR/em.in mdin1		# EM with Cuda support
	cp -v $INPDIR/nvt_r.in mdin2 		# Run to equilibrate Temperature with Berendsen
	cp -v $INPDIR/npt_r.in mdin3		# Run to equilbrate Density with Berendsen
	cp -v $INPDIR/pre_pull_r.in mdin4	# Run to equilibrate Density with adv. Barostat
	cp -v $INPDIR/pull_hreus.in mdin5	# Pull + equilibration for every umbrella Window
	cp -v $INPDIR/prod_uslj.in mdin6		# Production Run for every Umbrells Window
	cp -v $INPDIR/prod_usre.in mdin_usre
	cp -v $INPDIR/pull.r ./	
	cp -v $INPDIR/_lroa.r ./_lroa.r
	cp -v $INPDIR/_lroaus.r ./_lroaus.r
}

generate_run_files()
{
	cp -v inpcrd0 ./refc
	for i in 0 1 2 3 4
	do
		cp -v refc ./refc$i
	done
	
	k=0
	
	for i in $(seq 5 1 35)
	do
		sed "s/WINDOW/$i/g" mdin5 > mdin5.rep$i
		sed "s/WINDOW/$i/g" mdin6 > mdin6.rep$i
		sed "s/WINDOW/$i/g" mdin_usre > mdin_usre.rep$i
		sed "s/WINDOW/$i/g" pull.r > pull$i.r
		sed "s/WINDOW/$i/g" _lroaus.r > _lroaus$i.r
		sed -i "s/= 2.0, 2.0,/= 4.0, 4.0,/g" _lroaus$i.r
		k=$(( $k + 1 ))
	done
	
	echo "Generated $k umbrella sampling windows total"
}

copy_input_files
generate_run_files
