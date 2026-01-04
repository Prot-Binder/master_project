#!/bin/bash

export LC_NUMERIC=C  # Ensures decimal numbers use a dot instead of a comma

INPDIR="../_inp"
OUTDIR="_output"
TRASH="_trash"
JOBID="mhc"

MIN=5
STEP=1
MAX=40
replicaCount=$(seq $MIN $STEP $MAX | wc -l)
forceKs=( 8 8 8 8 8 8 8 8 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 )
mkdir -p $OUTDIR $TRASH

copy_input_files()
{
	
	cp -v $INPDIR/em.in mdin0		# EM with CPU (double precision)
	cp -v $INPDIR/em.in mdin1		# EM with Cuda support
	cp -v $INPDIR/nvt_r.in mdin2 		# Run to equilibrate Temperature with Berendsen
	cp -v $INPDIR/npt_r.in mdin3		# Run to equilbrate Density with Berendsen
	cp -v $INPDIR/pre_pull_r.in mdin4	# Run to equilibrate Density with adv. Barostat
	cp -v $INPDIR/pull_hreus.in mdin5	# Pull + equilibration for every umbrella Window
	cp -v $INPDIR/prod_us.in mdin6		# Production Run for every Umbrells Window

	cp -v $INPDIR/pull.r ./	
	cp -v $INPDIR/_lroa1.r ./_lroa.r
	cp -v $INPDIR/_lroaus1.r ./_lroaus.r
}

generate_run_files()
{

	cp -v inpcrd0 ./refc
	for i in 0 1 2 3 4
	do
		cp -v refc ./refc$i
	done

	#echo "# HREUS Run with adv. Free Binding Energy Calculation" > groupfile

	k=0
	for i in $(seq $MIN $STEP $MAX)
	do
		K_us=${forceKs[$k]}
		#echo "-O -i mdin6.rep$i -o $OUTDIR/mdout6.rep$i -p prmtop -c $OUTDIR/restrt5.rep$i -r $OUTDIR/restrt6.rep$i -x $OUTDIR/mdcrd6.rep$i -inf $OUTDIR/mdinfo6.rep$i" >> groupfile

		sed "s/WINDOW/$i/g" mdin5 > mdin5.rep$i
		sed "s/WINDOW/$i/g" mdin6 > mdin6.rep$i
		sed "s/WINDOW/$i/g" pull.r > pull$i.r
		sed "s/WINDOW/$i/g" _lroaus.r > _lroaus$i.r
		sed -i "s/= 2.0, 2.0,/= 4.0, 4.0,/g" _lroaus$i.r

		cp -v refc ./refc$i
		k=$(( $k + 1 ))
	done
}

run_HREUS()
{
	# run the em and equilibration
	eq_jobid=$(sbatch \
		--job-name=${JOBID}_eq \
		--gres=gpu:1 \
		--nodes=1 \
		--time=0-02:00:00 \
		--ntasks=1 \
		--cpus-per-task=1 \
		--exclude=t38cn030,t38cn038,t38cn028,t38cn015,t38cn024,t38cn027,t38cn016,t38cn018,t38cn031,t38cn020,t38cn021,t38cn032,t38cn019,t38cn022 \
		--output="$TRASH/slurm-%j.out" \
		run_rmd-seq_alex.sh 0 1 4)
	eq_jobid=$(echo $eq_jobid | awk '{print $NF}')

	# Run the Pull equilibration for every window in parallel
	#for rep in $(seq $MIN $STEP $MAX)
	#do
	#	pull_jobid=$(sbatch \
	#		--dependency=afterok:$eq_jobid \
	#		--job-name=${JOBID}_pull$rep \
	#		--gres=gpu:1 \
      	#		--nodes=1 \
      	#		--time=1-00:00:00 \
      	#		--ntasks=1 \
      	#		--cpus-per-task=1 \
      	#		--exclude=t38cn030,t38cn038,t38cn028,t38cn015,t38cn024,t38cn027,t38cn016,t38cn018,t38cn031,t38cn020,t38cn021,t38cn032,t38cn019,t38cn022 \
	#		--output="$TRASH/slurm-%j.out" \
	#		run_md_alex.sh 4 5.rep$rep \
	#		us.sh $rep)
	#done
		#pull_jobid=$(echo $pull_jobid | awk '{print $NF}')
		#pull_array+=($pull_jobid)
	#done
	
	# Process the Jobids so into one array delimitered by ':'
	#pull_jobids=$(printf ":%s" "${pull_array[@]}")
	#pull_jobids=${pull_jobids:1}
	#echo $pull_jobids

	# start the HREUS run, once all windows are ready from pull run
	#sbatch \
	#	--dependency=afterok:$pull_jobids \
	#	--job-name=${JOBID}_hreus \
	#	--time=1-00:00:00 \
	#	--export=none \
	#	--output="$TRASH/slurm-%j.out" \
	#	run_hreus_alex.sh $replicaCount
}

cleanup()
{
	ls -p | grep -v '.parmed\|.leapin\|.ipynb\|.sh\|.py\|/' | xargs -I '{}' -r mv -v '{}' $OUTDIR/ && echo " Done!" || echo "ERROR!"
}

#copy_input_files
#generate_run_files
run_HREUS
#rerun_md
#cleanup
