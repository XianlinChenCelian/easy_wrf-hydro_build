# Blank Windows Computer Setup

This is an optional appendix for private lab onboarding. The public project
assumes users already have Linux through native Linux, WSL2, or a VM.

Do not upload licensed Intel installers, license files, model source archives,
test data, or packed personal environments to the public GitHub repository.

## Private bundle layout

For a computer managed by your own laboratory, assemble a private folder from
software that the laboratory is licensed to use:

```text
private-wrf-hydro-bundle/
|-- Start-Here.ps1
|-- Data_Shared/
|   |-- <Intel installer and license, when legally permitted>
|   |-- wrf_hydro_nwm_public-5.1.2.tar.gz
|   |-- croton_NY_example_testcase.tar.gz
|   `-- libs/
|       |-- zlib-1.2.11.tar.gz
|       |-- hdf5-1.12.0.tar.gz
|       |-- netcdf-c-4.7.4.tar.gz
|       `-- netcdf-fortran-4.5.3.tar.gz
`-- easy_wrf-hydro_build/
```

Copy `scripts/windows/Start-Here.ps1` from this repository to the bundle root.
Review the script and the private package layout before using it on another
computer.

## Target computer

Open PowerShell as Administrator from the private bundle directory:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\Start-Here.ps1 -RunExample
```

The helper can install WSL2/Ubuntu when Windows supports `wsl --install`, then
continue inside Ubuntu. A Windows restart and one manual Ubuntu launch may be
required to create the Linux user. Rerun the same PowerShell command afterward.

The public WRF-Hydro workflow begins after Linux is available. For a strictly
air-gapped computer, prepare WSL itself through Microsoft's offline WSL process
before using the private bundle.

## Public release boundary

Only source code, documentation, examples, tests, CI, and page images belong in
this GitHub repository. The private bundle is a laboratory delivery artifact and
must remain outside Git history and GitHub Releases.
