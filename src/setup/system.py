from src.setup.tleap import TLeapPaths, run_tleap
from src.setup.hmr2 import ParmEdPaths, run_hmr
from src.setup.restraints import create_restraints
from pathlib import Path

# create initial topology, HMR, restraints, scaled toptologies, copy all files necessary for setup

def setup_simulation(cfg, setup_dir):

    # ---- 1) TLEAP (two-stage: volume -> ions -> final topology) ----
    # tleap_paths = TLeapPaths(
    #     template_tleap=Path("templates/tleap.in.tpl"),
    #     # template_final=Path("templates/tleap/tleap_final.in.tpl"),
    #     ff_leaprc_cyclic=Path("forcefield/leaprc.cyclic.ff14SB"),
    # )
# 
    # prmtop, rst, n_ions_each = run_tleap(
    #     setup_dir=setup_dir,
    #     pdb_path=cfg.system.pdb,
    #     bond=cfg.system.bond,  # may be None
    #     paths=tleap_paths,
    # )
# 
    # print(f"[setup] tleap done: {prmtop.name}, {rst.name} (ions each: {n_ions_each})")
# 
    # # ---- 2) ParmEd HMR ----
    # parmed_paths = ParmEdPaths(
    #     template=Path("templates/HMR.parmed.tpl"),
    # )
# 
    # hmr_prmtop = setup_dir / "prmtop"
    # run_hmr(
    #     setup_dir=setup_dir,
    #     in_prmtop=prmtop,
    #     out_prmtop=hmr_prmtop,
    #     paths=parmed_paths,
    # )
# 
    # print(f"[setup] HMR done: {hmr_prmtop.name}")
    # print(f"[setup] Results in: {setup_dir.resolve()}")

    # ---- 3) Generate Restraints ----
    system_pdb = setup_dir / "system.pdb"
    create_restraints(setup_dir, system_pdb, cfg.system.protein_residues, cfg.system.ligand_residues)
    
    print(f"[setup] Results in: {setup_dir.resolve()}")

    
