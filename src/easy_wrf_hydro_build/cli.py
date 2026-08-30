"""Command line interface for easy_wrf_hydro_build."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .bootstrap import BootstrapConfig, bootstrap
from .config import BuildConfig, CompileOptions
from .doctor import run_doctor
from .paths import EwhbCase
from .workflow import compile_wrf_hydro, write_runtime_env


def _compiler_defaults(args: argparse.Namespace) -> tuple[str, str]:
    if args.compiler_family == "gnu":
        return args.compiler_option or "gfort", args.mpi_wrapper or "mpif90"
    return args.compiler_option or "ifort", args.mpi_wrapper or "mpiifort"


def _build_config(args: argparse.Namespace) -> BuildConfig:
    compiler_option, mpi_wrapper = _compiler_defaults(args)
    options = CompileOptions(
        spatial_soil=args.spatial_soil,
        wrf_hydro_nudging=args.nudging,
        wrf_hydro_rapid=args.rapid,
        hydro_d=args.debug,
    )
    return BuildConfig(
        wrf_hydro_root=Path(args.wrf_hydro_root).expanduser().resolve(),
        netcdf=Path(args.netcdf).expanduser().resolve(),
        compiler_family=args.compiler_family,
        intel_home=Path(args.intel_home).expanduser().resolve() if args.intel_home else None,
        compiler_option=compiler_option,
        land_model=args.land_model,
        mpi_wrapper=mpi_wrapper,
        compile_options=options,
    )


def _add_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--wrf-hydro-root", required=True)
    parser.add_argument("--netcdf", required=True)
    parser.add_argument("--compiler-family", default="intel", choices=["intel", "gnu"])
    parser.add_argument("--intel-home")
    parser.add_argument("--compiler-option")
    parser.add_argument("--land-model", default="NoahMP", choices=["NoahMP", "Noah"])
    parser.add_argument("--mpi-wrapper")
    parser.add_argument("--spatial-soil", type=int, default=1, choices=[0, 1])
    parser.add_argument("--nudging", type=int, default=0, choices=[0, 1])
    parser.add_argument("--rapid", type=int, default=0, choices=[0, 1])
    parser.add_argument("--debug", type=int, default=0, choices=[0, 1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ewhb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_case = subparsers.add_parser("init-case", help="Create a standard WRF-Hydro case tree.")
    init_case.add_argument("--cases-home", required=True)
    init_case.add_argument("--case-name", required=True)

    doctor = subparsers.add_parser("doctor", help="Check compilers, MPI, NetCDF, and source paths.")
    _add_build_args(doctor)

    write_env = subparsers.add_parser("write-env", help="Write a reusable runtime environment script.")
    _add_build_args(write_env)
    write_env.add_argument("--output", required=True)

    compile_cmd = subparsers.add_parser("compile", help="Configure and compile WRF-Hydro.")
    _add_build_args(compile_cmd)
    compile_cmd.add_argument("--dry-run", action="store_true")

    bootstrap_cmd = subparsers.add_parser(
        "bootstrap",
        help="Build dependencies and WRF-Hydro from local source archives.",
    )
    bootstrap_cmd.add_argument("--shared-dir", required=True)
    bootstrap_cmd.add_argument("--prefix", required=True)
    bootstrap_cmd.add_argument("--intel-home")
    bootstrap_cmd.add_argument("--compiler-family", default="intel", choices=["intel", "gnu"])
    bootstrap_cmd.add_argument("--profile")
    bootstrap_cmd.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2)))
    bootstrap_cmd.add_argument("--compiler-option")
    bootstrap_cmd.add_argument("--land-model", default="NoahMP", choices=["NoahMP", "Noah"])
    bootstrap_cmd.add_argument("--mpi-wrapper")
    bootstrap_cmd.add_argument("--skip-deps", action="store_true")
    bootstrap_cmd.add_argument("--run-example", action="store_true")
    bootstrap_cmd.add_argument(
        "--example-config",
        default="NWM",
        choices=["NWM", "Gridded", "Gridded_no_lakes", "Reach", "ReachLakes"],
    )
    bootstrap_cmd.add_argument("--example-np", type=int, default=1)
    bootstrap_cmd.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "init-case":
        case = EwhbCase(Path(args.cases_home).expanduser().resolve(), args.case_name)
        case.builddir()
        print(case.case_dir)
        return 0

    if args.command == "doctor":
        ok = True
        for name, passed, detail in run_doctor(_build_config(args)):
            status = "OK" if passed else "FAIL"
            print(f"{status:4} {name:24} {detail}")
            ok = ok and passed
        return 0 if ok else 1

    if args.command == "write-env":
        output = write_runtime_env(_build_config(args), Path(args.output).expanduser().resolve())
        print(output)
        return 0

    if args.command == "compile":
        result = compile_wrf_hydro(_build_config(args), dry_run=args.dry_run)
        if isinstance(result, Path):
            print(result)
        else:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        return 0

    if args.command == "bootstrap":
        compiler_option, mpi_wrapper = _compiler_defaults(args)
        intel_home = Path(args.intel_home).expanduser().resolve() if args.intel_home else None
        if args.compiler_family == "intel" and intel_home is None:
            intel_home = Path("~/intel/parallel_studio_xe_2018").expanduser().resolve()
        result = bootstrap(
            BootstrapConfig(
                shared_dir=Path(args.shared_dir).expanduser().resolve(),
                prefix=Path(args.prefix).expanduser().resolve(),
                compiler_family=args.compiler_family,
                intel_home=intel_home,
                profile=args.profile,
                jobs=args.jobs,
                compiler_option=compiler_option,
                land_model=args.land_model,
                mpi_wrapper=mpi_wrapper,
                skip_deps=args.skip_deps,
                run_example=args.run_example,
                example_config=args.example_config,
                example_np=args.example_np,
            ),
            dry_run=args.dry_run,
        )
        if isinstance(result, Path):
            print(result)
        else:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
