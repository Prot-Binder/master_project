from src.setup.tleap import TLeapPaths, run_tleap
from src.setup.hmr2 import ParmEdPaths, run_hmr
from src.setup.restraints import create_restraints
from src.setup.generate_topology import generate_scaled_top_files
from src.setup.generate_input_files import generate_inputs
from pathlib import Path


def setup_simulation(cfg, setup_dir, top_dir):

    """
    # ---- 1) TLEAP (two-stage: volume -> ions -> final topology) ----
    tleap_paths = TLeapPaths(
        template_tleap=Path("templates/tleap.in.tpl"),
        # template_final=Path("templates/tleap/tleap_final.in.tpl"),
        ff_leaprc_cyclic=Path("forcefield/leaprc.cyclic.ff14SB"),
    )

    prmtop, rst, n_ions_each = run_tleap(
        setup_dir=setup_dir,
        pdb_path=cfg.system.pdb,
        bond=cfg.system.bond,  # may be None
        paths=tleap_paths,
    )

    print(f"[setup] tleap done: {prmtop.name}, {rst.name} (ions each: {n_ions_each})")

    # ---- 2) ParmEd HMR ----
    parmed_paths = ParmEdPaths(
        template=Path("templates/HMR.parmed.tpl"),
    )

    hmr_prmtop = setup_dir / "prmtop"
    run_hmr(
        setup_dir=setup_dir,
        in_prmtop=prmtop,
        out_prmtop=hmr_prmtop,
        paths=parmed_paths,
    )

    print(f"[setup] HMR done: {hmr_prmtop.name}")
    # ---- 3) Generate Restraints ----
    system_pdb = setup_dir / "system.pdb"
    create_restraints(setup_dir, system_pdb, cfg.system.protein_residues, cfg.system.ligand_residues)
    
    print(f"[setup] Restraints generated")

    # ---- 4) Generate Topology Files with different LJ parameters ----
    top_file = setup_dir / "prmtop"
    coord_file = setup_dir / "system.rst"
    scaled_topologies_dir = top_dir / "prmtop"
    generate_scaled_top_files(top_file, cfg.replica_scaling.n_rep, cfg.replica_scaling.d_scaling,
                              cfg.replica_scaling.e_scaling, coord_file, scaled_topologies_dir,
                              ":" + cfg.system.protein_residues, ":" + cfg.system.ligand_residues)
    """

    # ---- 5) Generate Input Files ----
    # gnerate dict

    _dict = {}
    _dict["paths"] = {}
    _dict["paths"]["templates_root"] = Path("templates")
    _dict["paths"]["results_root"] = Path("results")
    _dict["system"] = cfg.system.name
    _dict["tag"] = cfg.tag
    _dict["min"] = cfg.restraints.min
    _dict["max"] = cfg.restraints.max
    # generate_inputs("eq", _dict)
    generate_inputs("us", _dict)
