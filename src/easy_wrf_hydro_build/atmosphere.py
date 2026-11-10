"""Isolated WRF/WPS and coupled WRF | WRF-Hydro builds."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import tarfile


# These are reproducible project candidates, not an exclusive compatibility matrix.
ATMOSPHERE_PROFILES = {
    "5.1.2": {"wrf": "4.2", "wps": "4.2", "basis": "WRF v4.2 release notes"},
    "5.2.0": {"wrf": "4.3", "wps": "4.3", "basis": "WRF v4.3 release notes"},
    "5.4.0": {"wrf": "4.6.1", "wps": "4.6.0", "basis": "WRF-Hydro v5.4.0 tagged coupled tutorial"},
}

CONFIG_TOOLS = "automake-1.17.tar.gz"
GRIB_LIBRARIES = ("zlib-1.2.11.tar.gz", "libpng-1.2.50.tar.gz", "jasper-1.900.1.tar.gz")
SOURCE_HASHES = {
    "wrf_hydro_nwm_public-5.1.2.tar.gz": "203043916c94c597dd4204033715d0b2dc7907e2168cbe3dfef3cd9eef950eb7",
    "wrf_hydro_nwm_public-5.2.0.tar.gz": "7a3c95d52e1ef5681cc4c77f2c6a080dea6fd27c0e8b7ad30e205238062d9e87",
    "wrf_hydro_nwm_public-5.4.0.tar.gz": "bbe7e9e4a2f015426a77b22cda8d08a1bf54fc7ce4d0b35961de43dce8fef4a5",
    CONFIG_TOOLS: "397767d4db3018dd4440825b60c64258b636eaf6bf99ac8b0897f06c89310acd",
    "noahmp-848f54ad3d28c4303151fe5ad83724e232694422.tar.gz": "95977784760b53ba0a1eb31d470006ea4896937a5f5d1a3a3cc34cde9bdea363",
    "WRF-4.2.tar.gz": "c39a1464fd5c439134bbd39be632f7ce1afd9a82ad726737e37228c6a3d74706",
    "WPS-4.2.tar.gz": "3e175d033355d3e7638be75bc7c0bc0de6da299ebd175a9bbc1b7a121acd0168",
    "WRF-4.3.tar.gz": "68109070e3e6b3106257f738c0e69e774816589bf3a0cedaf66dd15f99ad63b5",
    "WPS-4.3.tar.gz": "1913cb24de549f029d65635feea27f3304a8f42ec025954a0887651fc89d1e9e",
    "WRF-4.6.1.tar.gz": "19bbd9977da9496cc15f5bb31aab8dc27045dc523968dded66cfd0f4746c40c4",
    "WPS-4.6.0.tar.gz": "ca7bbfc6c28a107c6eb00ded70e693f5c9a3926ecde7656f49e306c9eb9a309b",
    "zlib-1.2.11.tar.gz": "c3e5e9fdd5004dcb542feda5ee4f0ff0744628baf8ed2dd5d66f8ca1197cb1a1",
    "libpng-1.2.50.tar.gz": "7af08caebdb148604c302e2b2c645f68f2c53deb74e48131632d65f23a2cc58b",
    "jasper-1.900.1.tar.gz": "5a7b15aa653280c3e2f0a5b03b26e42fab7b56afa9fef56f485138d9b72b3e19",
}
SUBMODULES = {
    "phys/noahmp": "noahmp-848f54ad3d28c4303151fe5ad83724e232694422.tar.gz",
}
HYDRO_LAYOUT = {"5.1.2": "trunk/NDHMS", "5.2.0": "trunk/NDHMS", "5.4.0": "src"}
COUPLED_OPTIONS = {
    "WRF_HYDRO": "1", "HYDRO_D": "0", "SPATIAL_SOIL": "0", "WRF_HYDRO_RAPID": "0",
    "NCEP_WCOSS": "0", "NWM_META": "0", "WRF_HYDRO_NUDGING": "0",
    "HYDRO_REALTIME": "0", "OUTPUT_CHAN_CONN": "0", "PRECIP_DOUBLE": "0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_names(version: str, *, coupled: bool = False, build_wps: bool = True) -> list[str]:
    profile = ATMOSPHERE_PROFILES[version]
    names = [f"WRF-{profile['wrf']}.tar.gz"]
    if build_wps:
        names.extend((f"WPS-{profile['wps']}.tar.gz", *GRIB_LIBRARIES, CONFIG_TOOLS))
    if profile["wrf"] == "4.6.1":
        names.extend(SUBMODULES.values())
    if coupled:
        names.append(f"wrf_hydro_nwm_public-{version}.tar.gz")
    return names


def unpack(archive: Path, destination: Path) -> Path:
    """Extract an upstream single-root archive without escaping the build directory."""
    destination.mkdir(parents=True, exist_ok=False)
    base = destination.resolve()
    with tarfile.open(archive) as stream:
        for member in stream:
            if any(part.startswith("._") or part == "__MACOSX" for part in Path(member.name).parts):
                continue
            # The upstream WRFDA link points at an NCAR-only data directory.
            # em_real does not use it; all other external links are rejected.
            if (member.issym() and member.name == f"{archive.name.removesuffix('.tar.gz')}/var/run/crtm_coeffs"
                    and member.linkname == "/glade/work/wrfhelp/WRFDA_files/crtm_coeffs_2.3.0"):
                continue
            target = (base / member.name).resolve()
            if not target.is_relative_to(base):
                raise ValueError(f"Archive path escapes destination: {member.name}")
            if member.issym():
                if not (target.parent / member.linkname).resolve().is_relative_to(base):
                    raise ValueError(f"Archive link escapes destination: {member.name}")
            elif not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsupported archive entry: {member.name}")
            # Paths and link targets are checked immediately before each extraction.
            if hasattr(tarfile, "data_filter"):
                stream.extract(member, destination, filter="data")
            else:
                stream.extract(member, destination)
    # macOS can create AppleDouble files while applying metadata on exFAT.
    roots = [path for path in destination.iterdir() if not path.name.startswith("._")]
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError(f"Expected one source root in {archive}")
    return roots[0]


def configuration_choice(text: str, component: str, compiler: str,
                         system: str, machine: str) -> int:
    """Reproduce upstream menu enumeration, then choose an unambiguous toolchain."""
    modes = ("serial", "smpar", "dmpar", "dm+sm") if component == "WRF" else (
        "serial", "serial_NO_GRIB2", "dmpar", "dmpar_NO_GRIB2")
    wanted = "dmpar" if component == "WRF" else "serial"
    index = 0
    candidates = []
    for stanza in re.split(r"(?m)(?=^#ARCH)", text):
        header, _, settings = stanza.partition("\n")
        if not header.startswith("#ARCH") or system not in header:
            continue
        if system != "Darwin" and machine not in header:
            continue
        description = header[6:].split("#")[0].lower()
        label = re.search(r"(?m)^DESCRIPTION\s*=([^\n]+)", settings)
        specialization = description + (label.group(1).lower() if label else "")
        for mode in modes:
            if mode not in header:
                continue
            index += 1
            match = ("gfortran" in description if compiler == "gnu" else
                     ("intel" in description or "ifort" in description) and "oneapi" not in description)
            if compiler == "gnu" and system == "Darwin":
                match = match and "clang" in description
            if match and mode == wanted and not any(
                s in specialization for s in ("sgi", "poe", "cray", "mic", "avx", "phi", "hsw", "bdw", "knl")
            ):
                candidates.append(index)
    if len(candidates) != 1:
        raise ValueError(f"No unique {component} {compiler} configuration for {system}/{machine}; "
                         "this platform needs a separately validated build profile.")
    return candidates[0]


def patch_config(path: Path, values: dict[str, str]) -> None:
    text = path.read_text()
    for key, value in values.items():
        text, count = re.subn(rf"^{re.escape(key)}\s*=.*$", f"{key} = {value}", text,
                             flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"Expected one {key} assignment in {path}, got {count}")
    path.write_text(text)


def _patch_hydro_coupler(hydro: Path, version: str) -> None:
    if version == "5.2.0":
        # Hydro needs the WRF domain dimensions and its own communicator.
        coupler = hydro / "CPL/WRF_cpl/module_wrf_HYDRO.F"
        coupler.write_text(coupler.read_text().replace(
            "call MPP_LAND_INIT()",
            "call MPP_LAND_INIT(grid%e_we - grid%s_we - 1, grid%e_sn - grid%s_sn - 1)",
            1,
        ))
        mpp = hydro / "MPP/mpp_land.F"
        text = mpp.read_text().replace(
            "    global_nx = in_global_nx\n    global_ny = in_global_ny ",
            "    if (present(in_global_nx)) global_nx = in_global_nx\n"
            "    if (present(in_global_ny)) global_ny = in_global_ny",
            1,
        ).replace(
            '      if (ierr /= MPI_SUCCESS) call fatal_error_stop("MPI Error: MPI_INIT failed")\n'
            "      call MPI_COMM_DUP(MPI_COMM_WORLD, HYDRO_COMM_WORLD, ierr)",
            '      if (ierr /= MPI_SUCCESS) call fatal_error_stop("MPI Error: MPI_INIT failed")\n'
            "    endif\n"
            "    if (HYDRO_COMM_WORLD == MPI_COMM_NULL) then\n"
            "      call MPI_COMM_DUP(MPI_COMM_WORLD, HYDRO_COMM_WORLD, ierr)",
            1,
        )
        mpp.write_text(text)
    elif version == "5.4.0":
        # The legacy rule matches fortglob.f90 but passes fortglob.F90.
        fortglob = hydro / "utils/fortglob/Makefile"
        fortglob.write_text(fortglob.read_text().replace("$(*).F90", "$<"))
        # Every rank passes one routing output slice per soil level.
        routing_io = hydro / "Routing/module_NWM_io.F90"
        io_text = routing_io.read_text().replace(
            "allocate(globalOutComp(1,1,1))\n            allocate(globalOutReal(1,1,1))",
            "allocate(globalOutComp(1,numLev,1))\n            allocate(globalOutReal(1,numLev,1))",
            1,
        )
        # The gridded channel index is outside the model-variable loop.
        io_text = io_text.replace(
            "nf90_put_att(ftn,indexVarId,trim(fileMeta%crsCharAttNames(iTmp2)),trim(fileMeta%crsCharAttVals(iTmp2)))\n"
            "            call nwmCheck(diagFlag,iret,'ERROR: Unable to place esri_pe_string attribute into '//trim(fileMeta%varNames(iTmp)))",
            "nf90_put_att(ftn,indexVarId,trim(fileMeta%crsCharAttNames(iTmp2)),trim(fileMeta%crsCharAttVals(iTmp2)))\n"
            "            call nwmCheck(diagFlag,iret,'ERROR: Unable to place esri_pe_string attribute into index')",
            1,
        )
        routing_io.write_text(io_text)
    if version in {"5.2.0", "5.4.0"}:
        # Coupled WRF does not initialize the standalone orchestrator's NetCDF layer.
        extension = ".F90" if version == "5.4.0" else ".F"
        routing_io = hydro / "Routing" / ("module_NWM_io" + extension)
        routing_io.write_text(routing_io.read_text().replace(
            "orchestrator%IO_Manager%netcdf_layer%open_file(trim(nlst(1)%route_link_f)",
            "nf90_open(trim(nlst(1)%route_link_f)",
            1,
        ))


def build_atmosphere(archives: Path, prefix: Path, netcdf: Path, version: str,
                     compiler: str, jobs: int = 4, dry_run: bool = False, *,
                     coupled: bool = False, build_wps: bool = True,
                     hydro_archives: Path | None = None) -> dict:
    if jobs < 1:
        raise ValueError("jobs must be positive")
    profile = ATMOSPHERE_PROFILES[version]
    if hydro_archives is not None and not coupled:
        raise ValueError("--hydro-archives requires --coupled.")
    names = source_names(version, coupled=coupled, build_wps=build_wps)
    hydro_name = f"wrf_hydro_nwm_public-{version}.tar.gz"
    inputs = {name: (hydro_archives if name == hydro_name and hydro_archives is not None
                     else archives) / name for name in names}
    plan = {"wrf_hydro": version, **profile, "compiler": compiler,
            "mode": "coupled" if coupled else "atmosphere-only", "coupled_validation": "pending",
            "sources": names, "prefix": str(prefix), "netcdf": str(netcdf), "wps_build": build_wps}
    if coupled:
        plan.update(hydro_source=str(inputs[hydro_name]), hydro_source_layout=HYDRO_LAYOUT[version],
                    hydro_compile_options=COUPLED_OPTIONS.copy())
    if dry_run:
        return plan
    # WRF's legacy makefiles cannot reliably handle spaces in source/library paths.
    if any(re.search(r"[\s\\:$#(){}\[\]&;|<>`\"']", str(path)) for path in (prefix, netcdf)):
        raise ValueError("Choose build and NetCDF paths without whitespace or shell special characters.")
    if prefix.exists():
        raise ValueError("Use a fresh atmosphere prefix. Existing builds and failure logs are preserved.")
    system, machine = platform.system(), platform.machine()
    if compiler == "gnu":
        cc = os.environ.get("CC") or ("clang" if system == "Darwin" else "gcc")
        fc = os.environ.get("FC") or "gfortran"
        cxx = os.environ.get("CXX") or ("clang++" if system == "Darwin" else "g++")
        mpicc, mpifc = "mpicc", "mpif90"
    else:
        cc, fc, cxx, mpicc, mpifc = "icc", "ifort", "icpc", "mpiicc", "mpiifort"
    for tool in (cc, fc, mpicc, mpifc):
        if not shutil.which(tool):
            raise ValueError(f"Missing {tool}. Activate the matching toolchain; on HPC load administrator modules.")
    gnu_major = 0
    gnu_cpp = None
    if compiler == "gnu":
        gnu_major = int(subprocess.check_output([fc, "-dumpversion"], text=True).split(".")[0])
        if gnu_major < 9:
            raise ValueError("WRF/WPS needs GNU Fortran 9 or newer. Load matching MPI and NetCDF for that compiler.")
        if system == "Darwin":
            sibling = Path(shutil.which(fc)).with_name(Path(fc).name.replace("gfortran", "cpp"))
            gnu_cpp = shutil.which(str(sibling)) or shutil.which(os.environ.get("CPP", ""))
            if not gnu_cpp or "Free Software Foundation" not in subprocess.check_output(
                [gnu_cpp, "--version"], text=True,
            ):
                raise ValueError("On macOS, activate GNU cpp from the Fortran toolchain or set CPP to its path.")
    for tool in ("csh", "perl", "make", "m4", "cpp", "ar"):
        if not shutil.which(tool):
            raise ValueError(f"Missing host utility {tool}. Install it through your OS package manager "
                             "or ask your cluster administrator. See the WRF/WPS installation guide.")
    if coupled and not shutil.which("nm"):
        raise ValueError("Missing nm, used to verify that wrf.exe contains the WRF-Hydro coupler.")
    for name in ("include/netcdf.inc", "include/netcdf.mod", "bin/nf-config"):
        if not (netcdf / name).is_file():
            raise ValueError(f"Missing {netcdf / name}; select matching NetCDF-C and NetCDF-Fortran.")
    hashes = {}
    for name, path in inputs.items():
        hashes[name] = sha256(path)
        if hashes[name] != SOURCE_HASHES[name]:
            raise ValueError(f"SHA256 mismatch: {name}; obtain the exact pinned upstream source.")
    prefix.mkdir(parents=True)
    logs = prefix / "logs"
    logs.mkdir()
    plan.update(source_sha256=hashes, status="building", host=platform.node(),
                system=platform.system(), machine=platform.machine())
    report = prefix / "build-manifest.json"
    report.write_text(json.dumps(plan, indent=2) + "\n")
    env = os.environ.copy()
    # Inherit the explicitly activated toolchain, never source user login scripts.
    for key in ("WRF_CHEM", "WRF_KPP", "WRF_DA_CORE", "WRF_EM_CORE", "WRF_NMM_CORE",
                "WRFPLUS_DIR", "WRF_OS", "WRF_MACH", "PNETCDF", "PHDF5", "HDF5",
                "JASPERLIB", "JASPERINC"):
        env.pop(key, None)
    libs = prefix / "grib2"
    env.update(CC=cc, FC=fc, F77=fc, CXX=cxx,
               NETCDF=str(netcdf), WRF_HYDRO="0", WRF_EM_CORE="1", WRF_NMM_CORE="0")
    if build_wps:
        env.update(JASPERLIB=str(libs / "lib"), JASPERINC=str(libs / "include"))
    if coupled:
        env.update(COUPLED_OPTIONS, NETCDF_INC=str(netcdf / "include"), NETCDF_LIB=str(netcdf / "lib"))
    env["LD_LIBRARY_PATH"] = str(netcdf / "lib") + os.pathsep + env.get("LD_LIBRARY_PATH", "")

    def run(name, command, cwd, input_text=None, timeout=None):
        plan["stage"] = name
        report.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"Building {name}; log: {logs / (name + '.log')}", flush=True)
        with (logs / (name + ".log")).open("w") as output:
            subprocess.run(command, cwd=cwd, env=env, input=input_text, text=True,
                           stdout=output, stderr=subprocess.STDOUT, check=True, timeout=timeout)

    try:
        for tool in (cc, fc, mpicc, mpifc):
            run("toolchain-" + Path(tool).name, [tool, "--version"], prefix, timeout=30)
        probe = prefix / "netcdf_probe.f90"
        probe.write_text("program probe\nuse netcdf\nprint *, nf90_inq_libvers()\nend program\n")
        flags = subprocess.check_output([str(netcdf / "bin/nf-config"), "--flibs"],
                                        env=env, text=True)
        run("netcdf-probe-build", [mpifc, "-I" + str(netcdf / "include"), str(probe),
                                  "-o", str(prefix / "netcdf_probe"), *shlex.split(flags)], prefix)
        run("netcdf-probe-run", [str(prefix / "netcdf_probe")], prefix, timeout=30)
        modern_arm = machine in ("aarch64", "arm64") and compiler == "gnu"
        for name in GRIB_LIBRARIES if build_wps else ():
            source = unpack(archives / name, prefix / "sources" / name.removesuffix(".tar.gz"))
            options = [f"--prefix={libs}"]
            if name.startswith("zlib"):
                options += ["--static"]
                if system == "Darwin":
                    header = source / "zutil.h"
                    header.write_text(header.read_text().replace(
                        "#      ifndef fdopen", "#      if !defined(fdopen) && !defined(__APPLE__)"))
            else:
                options += ["--disable-shared", "--enable-static"]
                if system == "Darwin" and name.startswith("libpng"):
                    header = source / "pngconf.h"
                    header.write_text(header.read_text().replace(
                        "#  ifdef MACOS\n     /* We need", "#  if defined(MACOS) && !defined(__APPLE__)\n     /* We need"))
                if modern_arm:
                    # Old Autoconf support files predate aarch64 and Apple Silicon.
                    with tarfile.open(archives / CONFIG_TOOLS) as automake:
                        for helper in ("config.guess", "config.sub"):
                            payload = automake.extractfile(f"automake-1.17/lib/{helper}").read()
                            for old_script in source.rglob(helper):
                                old_script.write_bytes(payload)
            if name.startswith("jasper"):
                options += ["--disable-opengl", "--disable-libjpeg"]
            cflags = "-O2 -fPIC -std=gnu89" if modern_arm else "-O2 -fPIC"
            env.update(CFLAGS=cflags, CPPFLAGS=f"-I{libs / 'include'}",
                       LDFLAGS=f"-L{libs / 'lib'}")
            run(name + "-configure", ["./configure", *options], source)
            run(name + "-make", ["make", "-j", str(jobs)], source)
            run(name + "-install", ["make", "install"], source)
        if build_wps:
            for key in ("CFLAGS", "CPPFLAGS", "LDFLAGS"):
                env.pop(key, None)
        wrf = unpack(archives / f"WRF-{profile['wrf']}.tar.gz", prefix / "WRF")
        if coupled:
            source = unpack(inputs[hydro_name], prefix / "hydro-source") / HYDRO_LAYOUT[version]
            if not (source / "CPL/WRF_cpl/Makefile.cpl").is_file():
                raise ValueError(f"Missing WRF coupling source in {inputs[hydro_name]}.")
            hydro = wrf / "hydro"
            shutil.rmtree(hydro)
            source.rename(hydro)
            _patch_hydro_coupler(hydro, version)
        if profile["wrf"] == "4.6.1":
            for relative, name in SUBMODULES.items():
                source = unpack(archives / name, prefix / "sources" / name.removesuffix(".tar.gz"))
                shutil.copytree(source, wrf / relative, dirs_exist_ok=True)
        wps = unpack(archives / f"WPS-{profile['wps']}.tar.gz", prefix / "WPS") if build_wps else None
        env["WRF_DIR"] = str(wrf)
        for component, source in (("WRF", wrf), ("WPS", wps)):
            if source is None:
                continue
            if component == "WPS":
                env["WRF_HYDRO"] = "0"
            configure = source / "configure"
            configure_text = configure.read_text()
            if component == "WRF" and system == "Darwin":
                for library in ("libnetcdf", "libnetcdff"):
                    if f"{library}.dylib" not in configure_text:
                        configure_text = configure_text.replace(
                            f'-f "$NETCDF/lib/{library}.so"',
                            f'-f "$NETCDF/lib/{library}.so" -o -f "$NETCDF/lib/{library}.dylib"',
                        )
                io_makefile = source / "external/io_netcdf/makefile"
                if io_makefile.is_file():
                    io_text = io_makefile.read_text()
                    if "libnetcdff.dylib" not in io_text:
                        io_makefile.write_text(io_text.replace(
                            "-f $(NETCDFPATH)/lib/libnetcdff.so",
                            "-f $(NETCDFPATH)/lib/libnetcdff.so -o -f $(NETCDFPATH)/lib/libnetcdff.dylib",
                        ))
            elif component == "WPS":
                configure_text = configure_text.replace(
                    '[ -f "$NETCDF/lib/libnetcdff.a" ]',
                    '[ -f "$NETCDF/lib/libnetcdff.a" -o -f "$NETCDF/lib/libnetcdff.so" '
                    '-o -f "$NETCDF/lib/libnetcdff.dylib" ]',
                )
            configure.write_text(configure_text)
            defaults_path = source / "arch/configure.defaults"
            defaults = defaults_path.read_text()
            if system == "Linux" and machine == "aarch64" and compiler == "gnu":
                # Legacy tags lack an ARM64 menu entry for these portable GNU flags.
                if not re.search(r"(?m)^#ARCH.*Linux.*aarch64.*gfortran", defaults):
                    defaults = re.sub(r"(?m)^(#ARCH\s+Linux x86_64)([^\n]*gfortran[^\n]*)$",
                                      r"\1 aarch64\2", defaults)
                    defaults_path.write_text(defaults)
            choice = configuration_choice(defaults, component, compiler, system, machine)
            if compiler == "gnu":
                # Configure runs its own compiler and NetCDF probes before writing the result.
                # Use the activated compiler names at that stage as well as during make.
                for key, value in {"SFC": fc, "SCC": cc, "CCOMP": cc,
                                   "DM_FC": mpifc, "DM_CC": mpicc}.items():
                    defaults = re.sub(rf"(?m)^{key}[ \t]*=.*$", lambda _: f"{key} = {value}", defaults)
                defaults_path.write_text(defaults)
            run(component + "-configure", ["./configure"], source,
                f"{choice}\n1\n", timeout=180)
            config = source / ("configure.wrf" if component == "WRF" else "configure.wps")
            if not config.is_file():
                raise ValueError(f"{component} did not write {config.name}; inspect {logs / (component + '-configure.log')}.")
            if coupled and component == "WRF":
                macros = wrf / "hydro/macros"
                if not macros.is_file() or not (wrf / "hydro/Makefile.comm").is_file():
                    raise ValueError("WRF did not configure the Hydro coupler; inspect WRF-configure.log.")
                if compiler == "intel":
                    # The legacy Intel Hydro profile uses generic wrappers, which may invoke GNU.
                    wrappers = {"COMPILER90": mpifc}
                    if re.search(r"(?m)^COMPILERCC[ \t]*=", macros.read_text()):
                        wrappers["COMPILERCC"] = mpicc
                    patch_config(macros, wrappers)
                macro_text = macros.read_text()
                macro_text = re.sub(r"(?m)^NETCDFLIB\s*=.*$", "NETCDFLIB = -L$(NETCDF_LIB) -lnetcdff -lnetcdf",
                                    macro_text)
                if gnu_major >= 10:
                    macro_text += "\nF90FLAGS += -fallow-argument-mismatch\n"
                macros.write_text(macro_text)
            c_compat = ""
            if (gnu_major >= 14 or (compiler == "gnu" and system == "Darwin")):
                # Legacy GRIB utilities still use C declarations accepted by older compilers.
                c_compat = " -std=gnu17 -Wno-error=implicit-function-declaration -Wno-error=implicit-int"
            settings = {"SFC": fc, "SCC": cc + c_compat,
                        "DM_FC": mpifc, "DM_CC": mpicc + c_compat}
            if component == "WRF":
                settings["CCOMP"] = cc + c_compat
                if c_compat:
                    settings["CC_TOOLS"] = "$(SCC)"
            if gnu_cpp:
                settings["CPP"] = f"{gnu_cpp} -P " + ("-nostdinc" if component == "WRF" else "-traditional")
            patch_config(config, settings)
            if gnu_major >= 10 and component == "WPS" and profile["wps"] in ("4.2", "4.3"):
                with config.open("a") as stream:
                    stream.write("\nFFLAGS += -fallow-argument-mismatch\nF77FLAGS += -fallow-argument-mismatch\n")
            if gnu_major >= 10 and component == "WRF":
                config_text = config.read_text()
                flags = [flag for flag in ("-fallow-argument-mismatch", "-fallow-invalid-boz")
                         if flag not in config_text]
                if flags:
                    with config.open("a") as stream:
                        stream.write("\nFCBASEOPTS_NO_G += " + " ".join(flags) + "\n")
            command = ["./compile", "em_real", "-j", str(jobs)] if component == "WRF" else ["./compile"]
            run(component + "-compile", command, source)
            required = ("main/wrf.exe", "main/real.exe", "external/io_netcdf/libwrfio_nf.a") if component == "WRF" else (
                "geogrid.exe", "ungrib.exe", "metgrid.exe")
            for relative in required:
                result = source / relative
                if not result.is_file() or result.stat().st_size == 0:
                    compile_log = logs / f"{component}-compile.log"
                    with compile_log.open(errors="replace") as stream:
                        killed = any("Killed signal terminated program" in line or
                                     "out of memory" in line.lower() for line in stream)
                    detail = f"{component} did not produce {relative}; inspect {compile_log}."
                    if killed:
                        detail += " A compiler process was killed. Check the memory limit and retry with --jobs 1."
                    raise ValueError(detail)
                if relative.endswith(".exe") and not os.access(result, os.X_OK):
                    raise ValueError(f"{result} is not executable; check filesystem permissions/noexec.")
            if coupled and component == "WRF":
                library = wrf / "hydro/lib/libHYDRO.a"
                if not library.is_file() or not library.stat().st_size:
                    raise ValueError("WRF did not build hydro/lib/libHYDRO.a; inspect WRF-compile.log.")
                run("WRF-coupling-symbols", ["nm", "-g", str(wrf / "main/wrf.exe")], wrf)
                symbols = (logs / "WRF-coupling-symbols.log").read_text(errors="replace")
                if not re.search(r"(?mi)\bT\s+_?wrf_drv_hydro_+\s*$", symbols):
                    raise ValueError("wrf.exe lacks the linked WRF-Hydro driver; inspect WRF-coupling-symbols.log.")
                plan.update(coupled_validation="linked", hydro_library=str(library))
        plan.update(status="compiled", wrf_dir=str(wrf), wps_dir=str(wps) if wps else None,
                    runtime_validation="pending")
    except Exception as error:
        plan.update(status="failed", error=str(error))
        raise
    finally:
        report.write_text(json.dumps(plan, indent=2) + "\n")
    return plan
