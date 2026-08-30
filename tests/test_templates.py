from pathlib import Path, PurePosixPath

from easy_wrf_hydro_build.bootstrap import BootstrapConfig, bootstrap_script
from easy_wrf_hydro_build.archives import SourceArchive
from easy_wrf_hydro_build import BuildConfig
from easy_wrf_hydro_build.templates import compile_driver_script


def test_compile_driver_prefers_mpiifort():
    config = BuildConfig(
        wrf_hydro_root=Path("/tmp/wrfhydro/trunk/NDHMS"),
        netcdf=Path("/tmp/netcdf"),
        compiler_family="intel",
        intel_home=Path("/opt/intel"),
    )
    script = compile_driver_script(config, "setEnvar_easy_wrf_hydro.sh")
    assert "COMPILER90  = mpiifort" in script
    assert "./configure ifort" in script


def test_bootstrap_script_can_run_croton_example():
    config = BootstrapConfig(
        shared_dir=PurePosixPath("/shared"),
        prefix=PurePosixPath("/work/wrfhydro"),
        compiler_family="intel",
        intel_home=PurePosixPath("/opt/intel"),
        run_example=True,
    )
    archives = {
        "zlib": SourceArchive("zlib", PurePosixPath("/shared/libs/zlib-1.2.11.tar.gz")),
        "hdf5": SourceArchive("hdf5", PurePosixPath("/shared/libs/hdf5-1.12.0.tar.gz")),
        "netcdf_c": SourceArchive("netcdf_c", PurePosixPath("/shared/libs/netcdf-c-4.7.4.tar.gz")),
        "netcdf_fortran": SourceArchive(
            "netcdf_fortran",
            PurePosixPath("/shared/libs/netcdf-fortran-4.5.3.tar.gz"),
        ),
        "wrf_hydro": SourceArchive(
            "wrf_hydro",
            PurePosixPath("/shared/wrf_hydro_nwm_public-5.1.2.tar.gz"),
        ),
        "croton_example": SourceArchive(
            "croton_example",
            PurePosixPath("/shared/croton_NY_example_testcase.tar.gz"),
        ),
    }

    script = bootstrap_script(config, archives)

    assert "CROTON_EXAMPLE_ARCHIVE=/shared/croton_NY_example_testcase.tar.gz" in script
    assert "mpirun -np 1 ./wrf_hydro_NoahMP.exe" in script


def test_bootstrap_script_supports_gnu_profile():
    config = BootstrapConfig(
        shared_dir=PurePosixPath("/shared"),
        prefix=PurePosixPath("/work/wrfhydro"),
        compiler_family="gnu",
        compiler_option="gfort",
        mpi_wrapper="mpif90",
    )
    archives = {
        "zlib": SourceArchive("zlib", PurePosixPath("/shared/libs/zlib-1.2.11.tar.gz")),
        "hdf5": SourceArchive("hdf5", PurePosixPath("/shared/libs/hdf5-1.12.0.tar.gz")),
        "netcdf_c": SourceArchive("netcdf_c", PurePosixPath("/shared/libs/netcdf-c-4.7.4.tar.gz")),
        "netcdf_fortran": SourceArchive(
            "netcdf_fortran",
            PurePosixPath("/shared/libs/netcdf-fortran-4.5.3.tar.gz"),
        ),
        "wrf_hydro": SourceArchive(
            "wrf_hydro",
            PurePosixPath("/shared/wrf_hydro_nwm_public-5.1.2.tar.gz"),
        ),
    }

    script = bootstrap_script(config, archives)

    assert 'NETCDF="$PREFIX/gnu_libs"' in script
    assert "export FC=gfortran" in script
    assert "./configure gfort" in script
    assert "COMPILER90  = mpif90" in script
    assert "wrf_hydro_gnu_env.sh" in script
