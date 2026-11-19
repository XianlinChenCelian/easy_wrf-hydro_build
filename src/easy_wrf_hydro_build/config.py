"""Build configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CompileOptions:
    wrf_hydro: int = 1
    hydro_d: int = 0
    spatial_soil: int = 1
    wrf_hydro_rapid: int = 0
    wrfio_ncd_large_file_support: int = 1
    ncep_wcoss: int = 0
    wrf_hydro_nudging: int = 0

    def as_env(self) -> dict[str, str]:
        return {
            "WRF_HYDRO": str(self.wrf_hydro),
            "HYDRO_D": str(self.hydro_d),
            "SPATIAL_SOIL": str(self.spatial_soil),
            "WRF_HYDRO_RAPID": str(self.wrf_hydro_rapid),
            "WRFIO_NCD_LARGE_FILE_SUPPORT": str(self.wrfio_ncd_large_file_support),
            "NCEP_WCOSS": str(self.ncep_wcoss),
            "WRF_HYDRO_NUDGING": str(self.wrf_hydro_nudging),
        }

    def to_shell_exports(self) -> str:
        return "\n".join(f"export {key}={value}" for key, value in self.as_env().items()) + "\n"


@dataclass(frozen=True)
class BuildConfig:
    wrf_hydro_root: Path
    netcdf: Path
    compiler_family: str = "intel"
    intel_home: Path | None = None
    mpi_wrapper: str = "mpiifort"
    compiler_option: str = "ifort"
    land_model: str = "NoahMP"
    compile_options: CompileOptions = field(default_factory=CompileOptions)
    run_dir: Path | None = None

    @property
    def uses_cmake(self) -> bool:
        return (self.wrf_hydro_root / "CMakeLists.txt").is_file()

    @property
    def model_run_dir(self) -> Path:
        if self.run_dir is not None:
            return self.run_dir
        if not self.uses_cmake:
            return self.wrf_hydro_root / "Run"
        sources = self.wrf_hydro_root.parent
        if sources.name == "sources":
            return sources.parent / "build" / "Run"
        raise ValueError("Pass --run-dir pointing to the Run directory of this CMake build.")

    @property
    def netcdf_inc(self) -> Path:
        return self.netcdf / "include"

    @property
    def netcdf_lib(self) -> Path:
        return self.netcdf / "lib"

    @property
    def compile_script(self) -> str:
        if self.land_model.lower() == "noahmp":
            return "./compile_offline_NoahMP.sh"
        if self.land_model.lower() == "noah":
            return "./compile_offline_Noah.sh"
        raise ValueError(f"Unsupported land model: {self.land_model}")
