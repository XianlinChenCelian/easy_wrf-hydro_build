"""Command line interface for easy_wrf_hydro_build."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from tarfile import TarError
from zipfile import BadZipFile

from .archives import WRF_HYDRO_RELEASES
from .atmosphere import build_atmosphere
from .bootstrap import BootstrapConfig, bootstrap
from .config import BuildConfig, CompileOptions
from .doctor import run_doctor
from .domain import fetch_geog, prepare_domain
from .forcing import DOWNLOAD_PRODUCTS, PRODUCTS, fetch_weather as download_weather, prepare_forcing, prepare_weather
from .paths import EwhbCase
from .workflow import compile_wrf_hydro, write_runtime_env


def _compiler_defaults(args: argparse.Namespace) -> tuple[str, str]:
    if args.compiler_family == "gnu":
        return args.compiler_option or "gfort", args.mpi_wrapper or "mpif90"
    compiler = args.compiler_option or "ifort"
    wrapper = "mpiifx" if compiler == "ifx" else "mpiifort"
    return compiler, args.mpi_wrapper or wrapper


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
    intel_setup = bootstrap_cmd.add_mutually_exclusive_group()
    intel_setup.add_argument("--intel-home")
    intel_setup.add_argument("--site-toolchain", action="store_true", help="Use the administrator-provided Intel compiler and MPI already loaded in this shell.")
    bootstrap_cmd.add_argument(
        "--wrf-hydro-version",
        choices=WRF_HYDRO_RELEASES,
        help="Select a WRF-Hydro release and its matching Croton archive.",
    )
    bootstrap_cmd.add_argument("--netcdf", help="Use existing NetCDF-C and NetCDF-Fortran libraries.")
    bootstrap_cmd.add_argument("--build-netcdf", action="store_true", help="Build NetCDF and its dependencies from source archives.")
    bootstrap_cmd.add_argument("--compiler-family", choices=["intel", "gnu"])
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

    atmosphere = subparsers.add_parser("build-atmosphere", help="Build optional WRF and WPS in a fresh directory (preview).")
    atmosphere.add_argument("--shared-dir", required=True)
    atmosphere.add_argument("--prefix", required=True)
    atmosphere.add_argument("--netcdf", required=True)
    atmosphere.add_argument("--wrf-hydro-version", choices=WRF_HYDRO_RELEASES, required=True)
    atmosphere.add_argument("--compiler-family", choices=["gnu", "intel"], required=True)
    atmosphere.add_argument("--jobs", type=int, default=4)
    atmosphere.add_argument("--dry-run", action="store_true")

    domain = subparsers.add_parser(
        "prepare-domain", help="Prepare WPS, routing and Noah-MP inputs for an offline basin (preview).",
    )
    domain.add_argument("--config", required=True, type=Path)
    domain.add_argument("--output", required=True, type=Path)
    domain.add_argument("--geogrid-only", action="store_true")

    geog = subparsers.add_parser("fetch-geog", help="Cache reusable NCAR WPS static datasets.")
    geog.add_argument("--cache", required=True, type=Path)
    geog.add_argument("--resolution", choices=("high", "low"), default="high")
    geog.add_argument("--archive", type=Path, help="Use a previously downloaded NCAR archive.")

    forcing = subparsers.add_parser("prepare-forcing", help="Convert weather inputs to offline HRLDAS forcing.")
    weather_source = forcing.add_mutually_exclusive_group(required=True)
    weather_source.add_argument("--config", type=Path, help="JSON configuration, including custom sources.")
    weather_source.add_argument("--source", choices=PRODUCTS, help="Use a built-in weather product profile.")
    forcing.add_argument("--input", dest="files", nargs="+",
                         help="Local NetCDF, CDS ZIP, Zarr v2, or quoted globs.")
    forcing.add_argument("--geogrid", help="WPS geo_em.d01.nc for the model land grid.")
    forcing.add_argument("--start", help="Model start time, ISO 8601 with UTC offset.")
    forcing.add_argument("--end", help="Model end time, ISO 8601 with UTC offset.")
    forcing.add_argument("--accumulation", choices=("daily", "hourly"), help="Override accumulation for ERA5-Land.")
    forcing.add_argument("--output", type=Path, required=True)
    forcing.add_argument("--run-dir", type=Path, help="Link a new FORCING directory into an existing run.")

    fetch_weather = subparsers.add_parser("fetch-forcing", help="Download domain weather data to a local cache.")
    fetch_weather.add_argument("--source", choices=DOWNLOAD_PRODUCTS, required=True)
    fetch_weather.add_argument("--geogrid", type=Path, required=True)
    fetch_weather.add_argument("--start", required=True, help="Model start time, ISO 8601 with UTC offset.")
    fetch_weather.add_argument("--end", required=True, help="Model end time, ISO 8601 with UTC offset.")
    fetch_weather.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command in {"prepare-forcing", "fetch-forcing"}:
        command = forcing if args.command == "prepare-forcing" else fetch_weather
        try:
            output = args.output.expanduser().resolve()
            if args.command == "prepare-forcing":
                run_dir = args.run_dir.expanduser().resolve() if args.run_dir else None
                direct = {key: getattr(args, key) for key in ("files", "geogrid", "start", "end", "accumulation")}
                if args.config:
                    if any(value is not None for value in direct.values()):
                        forcing.error("Use either --config or the direct source arguments.")
                    result = prepare_forcing(args.config.expanduser().resolve(), output, run_dir)
                else:
                    if not all(direct[key] for key in ("files", "geogrid", "start", "end")):
                        forcing.error("--source requires --input, --geogrid, --start, and --end.")
                    config = {key: value for key, value in direct.items() if value is not None}
                    result = prepare_weather({"source": args.source, **config}, Path.cwd(), output, run_dir)
            else:
                result = download_weather(args.source, args.geogrid.expanduser().resolve(),
                                          args.start, args.end, output)
        except ModuleNotFoundError as exc:
            command.error(f"Missing {exc.name}. Activate the forcing environment (docs/forcing.md).")
        except (ValueError, OSError, KeyError, TypeError, RuntimeError, BadZipFile) as exc:
            command.error(str(exc))
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "prepare-domain":
        try:
            result = prepare_domain(args.config.expanduser().resolve(),
                                    args.output.expanduser().resolve(),
                                    geogrid_only=args.geogrid_only)
        except ModuleNotFoundError as exc:
            domain.error(f"Missing {exc.name}. Run in the domain environment (see docs/domain-preparation.md).")
        except (ValueError, OSError, KeyError, TypeError, RuntimeError, BadZipFile) as exc:
            domain.error(str(exc))
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "fetch-geog":
        try:
            result = fetch_geog(args.cache.expanduser().resolve(), args.resolution,
                                args.archive.expanduser().resolve() if args.archive else None)
        except (ValueError, OSError, TarError) as exc:
            geog.error(str(exc))
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "build-atmosphere":
        try:
            result = build_atmosphere(
                Path(args.shared_dir).expanduser().resolve(), Path(args.prefix).expanduser().resolve(),
                Path(args.netcdf).expanduser().resolve(), args.wrf_hydro_version,
                args.compiler_family, args.jobs, args.dry_run,
            )
        except (ValueError, OSError, CalledProcessError, TimeoutExpired) as exc:
            atmosphere.error(str(exc))
        print(json.dumps(result, indent=2))
        return 0

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
        if args.compiler_family is None:
            args.compiler_family = "intel" if args.site_toolchain or not args.wrf_hydro_version else "gnu"
        compiler_option, mpi_wrapper = _compiler_defaults(args)
        intel_home = Path(args.intel_home).expanduser().resolve() if args.intel_home else None
        if args.compiler_family == "intel" and intel_home is None and not args.site_toolchain:
            intel_home = Path("~/intel/parallel_studio_xe_2018").expanduser().resolve()
        try:
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
                    wrf_hydro_version=args.wrf_hydro_version,
                    netcdf_prefix=Path(args.netcdf).expanduser().resolve() if args.netcdf else None,
                    build_netcdf=args.build_netcdf,
                    site_toolchain=args.site_toolchain,
                ),
                dry_run=args.dry_run,
            )
        except (ValueError, FileNotFoundError) as exc:
            bootstrap_cmd.error(str(exc))
        except CalledProcessError as exc:
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
            return exc.returncode if exc.returncode > 0 else 1
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
