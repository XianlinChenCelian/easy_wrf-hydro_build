"""Run the bundled, single-domain GFS and WRF-Hydro examples."""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess

from .atmosphere import sha256
from .domain import _namelist


BASINS = ("jing", "gasconade")
DOMAIN_FILES = (
    "Fulldom_hires.nc", "GEOGRID_LDASOUT_Spatial_Metadata.nc", "Route_Link.nc",
)


def _wrf_namelist(case, start, end):
    domain = case["domain"]
    return f"""&time_control
 run_hours = {int((end - start).total_seconds() / 3600)},
 start_year = {start.year}, start_month = {start.month}, start_day = {start.day},
 start_hour = {start.hour},
 end_year = {end.year}, end_month = {end.month}, end_day = {end.day},
 end_hour = {end.hour},
 interval_seconds = {case['interval_seconds']},
 input_from_file = .true., history_interval = 60,
 frames_per_outfile = 1, restart = .false., restart_interval = 1440,
 io_form_history = 2, io_form_restart = 2, io_form_input = 2, io_form_boundary = 2,
 use_netcdf_classic = .true.,
/
&domains
 time_step = 60, max_dom = 1,
 e_we = {domain['e_we']}, e_sn = {domain['e_sn']}, e_vert = 35,
 num_metgrid_levels = 34, num_metgrid_soil_levels = 4,
 dx = {domain['cell_m']}, dy = {domain['cell_m']},
 grid_id = 1, parent_id = 0, i_parent_start = 1, j_parent_start = 1,
 parent_grid_ratio = 1, parent_time_step_ratio = 1,
 p_top_requested = 5000,
/
&physics
 mp_physics = 3, ra_lw_physics = 1, ra_sw_physics = 1, radt = 15,
 sf_sfclay_physics = 1, sf_surface_physics = 4, bl_pbl_physics = 1,
 cu_physics = 1, cudt = 5, icloud = 1,
 num_soil_layers = 4, num_land_cat = 21, sf_urban_physics = 0,
/
&noah_mp
 dveg = 4, opt_crs = 1, opt_btr = 1, opt_run = 3, opt_sfc = 1,
 opt_frz = 1, opt_inf = 1, opt_rad = 3, opt_alb = 2,
 opt_snf = 1, opt_tbot = 2, opt_stc = 1,
/
&dynamics
 diff_opt = 1, km_opt = 4, diff_6th_opt = 0,
 damp_opt = 0, non_hydrostatic = .true., gwd_opt = 0,
/
&bdy_control
 spec_bdy_width = 5, specified = .true.,
/
&namelist_quilt
 nio_tasks_per_group = 0, nio_groups = 1,
/
"""


def _hydro_namelist(case):
    routing = case["routing"]
    return f"""&HYDRO_nlist
 sys_cpl = 2, igrid = 1,
 geo_static_flnm = 'geo_em.d01.nc',
 geo_finegrid_flnm = 'DOMAIN/Fulldom_hires.nc',
 land_spatial_meta_flnm = 'DOMAIN/GEOGRID_LDASOUT_Spatial_Metadata.nc',
 hydrotbl_f = 'hydro2dtbl.nc',
 route_link_f = 'DOMAIN/Route_Link.nc',
 rst_dt = 1440, rst_typ = 1, rst_bi_in = 0, rst_bi_out = 0,
 rstrt_swc = 1, gw_restart = 0,
 out_dt = 60, split_output_count = 1, order_to_write = 1,
 io_form_outputs = 4, io_config_outputs = 0, t0OutputFlag = 1,
 CHRTOUT_DOMAIN = 1, CHANOBS_DOMAIN = 1, CHRTOUT_GRID = 0,
 LSMOUT_DOMAIN = 1, RTOUT_DOMAIN = 1, output_gw = 0, outlake = 0, frxst_pts_out = 0,
 nsoil = 4, zsoil8 = -0.10, -0.40, -1.00, -2.00,
 dxrt = {routing['spacing_m']}, aggfactrt = {routing['ratio']},
 dtrt_ch = 30, dtrt_ter = 30,
 subrtswcrt = 1, ovrtswcrt = 1, rt_option = 1,
 chanrtswcrt = 1, channel_option = 2, gwbaseswcrt = 0, udmp_opt = 0,
/
"""


def _stage(command, folder, name, marker, log_file=None):
    stdout = folder / f"{name}.stdout.log"
    check = folder / log_file if log_file else stdout
    print(f"Running {name}. Log: {stdout}", flush=True)
    with stdout.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=folder, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode or not check.is_file() or marker not in check.read_text(errors="replace"):
        logs = f"{stdout} and {check}" if log_file else str(stdout)
        raise ValueError(f"{name} failed (exit {result.returncode}). See {logs}.")


def run_basin(case_dir: Path, build_dir: Path, output: Path,
              *, geog: Path | None = None, wps_dir: Path | None = None, ranks: int = 1):
    if ranks < 1:
        raise ValueError("--ranks must be positive.")
    if geog is None:
        geog = case_dir.parent.parent / "static/WPS_GEOG"
    if not geog.is_dir():
        raise ValueError(f"Missing WPS static data directory: {geog}. Use the bundled geography "
                         "or pass --geog-data with an NCAR WPS_GEOG cache.")
    if output.exists():
        raise ValueError("Choose a fresh output directory to preserve previous model files and logs.")
    case = json.loads((case_dir / "case.json").read_text())
    build = json.loads((build_dir / "build-manifest.json").read_text())
    if build.get("status") != "compiled" or build.get("coupled_validation") != "linked":
        raise ValueError("Use a completed ewhb build-atmosphere --coupled installation.")
    if build["wrf_hydro"] != case["wrf_hydro"]:
        raise ValueError(f"This case targets WRF-Hydro {case['wrf_hydro']}.")
    wrf = Path(build["wrf_dir"])
    if wps_dir is None:
        if not build["wps_dir"]:
            raise ValueError("Pass --wps for a coupled build that reused an existing WPS.")
        wps_dir = Path(build["wps_dir"])
    for exe in (*(wps_dir / f"{name}.exe" for name in ("geogrid", "ungrib", "metgrid")),
                wrf / "main/real.exe", wrf / "main/wrf.exe"):
        if not exe.is_file() or not os.access(exe, os.X_OK):
            raise ValueError(f"Executable missing or inaccessible: {exe}")
    if not shutil.which("mpirun"):
        raise ValueError("Activate the MPI environment used to compile WRF and try again.")
    start = datetime.fromisoformat(case["cycle_utc"])
    interval = case["interval_seconds"]
    files = case["grib2"]
    for filename in files:
        if Path(filename).name != filename:
            raise ValueError(f"Expected a bundled GFS filename: {filename}")
        source = case_dir / "GFS" / filename
        if sha256(source) != case["weather_files"][filename]["sha256"]:
            raise ValueError(f"Incorrect checksum for bundled GFS input: {source}")
    end = start + timedelta(seconds=interval * (len(files) - 1))
    times = [(start + timedelta(seconds=interval * i)).strftime("%Y-%m-%d_%H:%M:%S")
             for i in range(len(files))]
    # A short relative path also fits the legacy WPS tile filename buffer.
    namelist = _namelist(case["domain"], case["domain"]["e_we"], case["domain"]["e_sn"], "WPS_GEOG",
                         "default", start=times[0], end=times[-1], interval=interval)

    output.mkdir(parents=True)
    wps = output / "wps"
    run = output / "run"
    wps.mkdir()
    run.mkdir()
    (wps / "WPS_GEOG").symlink_to(geog, target_is_directory=True)
    (wps / "namelist.wps").write_text(namelist + """&ungrib
 out_format = 'WPS', prefix = 'GFS',
/
&metgrid
 fg_name = 'GFS', io_form_metgrid = 2,
/
""", encoding="utf-8")
    for component, table in (("geogrid", "GEOGRID.TBL"), ("metgrid", "METGRID.TBL")):
        (wps / component).mkdir()
        shutil.copyfile(wps_dir / component / (table + ".ARW"), wps / component / table)
    (wps / "Vtable").symlink_to(wps_dir / "ungrib/Variable_Tables/Vtable.GFS")
    for suffix, filename in zip(("AAA", "AAB", "AAC"), files, strict=True):
        (wps / f"GRIBFILE.{suffix}").symlink_to(case_dir / "GFS" / filename)
    for name in ("geogrid", "ungrib", "metgrid"):
        _stage([str(wps_dir / f"{name}.exe")], wps, name, "Successful completion")
    for filename in ("geo_em.d01.nc", *(f"met_em.d01.{time}.nc" for time in times)):
        if not (wps / filename).stat().st_size:
            raise ValueError(f"Empty WPS output: {wps / filename}")
        (run / filename).symlink_to(wps / filename)

    for file in (wrf / "run").iterdir():
        if (file.is_file() and not file.name.startswith("namelist.")
                and file.name not in {"real.exe", "wrf.exe", "HYDRO.TBL", "CHANPARM.TBL"}):
            (run / file.name).symlink_to(file)
    shutil.copyfile(case_dir / "HYDRO.TBL", run / "HYDRO.TBL")
    shutil.copyfile(wrf / "hydro/template/HYDRO/CHANPARM.TBL", run / "CHANPARM.TBL")
    shutil.copyfile(wrf / "hydro/template/NoahMP/namelist.hrldas", run / "namelist.hrldas")
    (run / "DOMAIN").mkdir()
    for filename in DOMAIN_FILES:
        shutil.copyfile(case_dir / "DOMAIN" / filename, run / "DOMAIN" / filename)
    (run / "namelist.input").write_text(_wrf_namelist(case, start, end), encoding="utf-8")
    (run / "hydro.namelist").write_text(_hydro_namelist(case), encoding="utf-8")
    launcher = ["mpirun", "-np", str(ranks)]
    _stage([*launcher, str(wrf / "main/real.exe")], run, "real", "SUCCESS COMPLETE REAL_EM INIT", "rsl.error.0000")
    for log in run.glob("rsl.*"):
        log.rename(run / f"real.{log.name}")
    _stage([*launcher, str(wrf / "main/wrf.exe")], run, "wrf", "SUCCESS COMPLETE WRF", "rsl.error.0000")
    outputs = ("wrfinput_d01", "wrfbdy_d01", f"wrfout_d01_{times[-1]}",
               f"{end:%Y%m%d%H%M}.CHRTOUT_DOMAIN1", f"{end:%Y%m%d%H%M}.CHANOBS_DOMAIN1",
               f"{end:%Y%m%d%H%M}.RTOUT_DOMAIN1")
    for name in outputs:
        if not (run / name).stat().st_size:
            raise ValueError(f"Empty coupled output: {run / name}")
    report = {"case": case["basin"], "wrf_hydro": case["wrf_hydro"], "ranks": ranks,
              "start_utc": times[0], "end_utc": times[-1], "files": [str(run / name) for name in outputs],
              "status": "completed"}
    (output / "run-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
