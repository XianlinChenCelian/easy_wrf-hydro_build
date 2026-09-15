# Runnable Examples

[Quickstart](../docs/quickstart.md) · [CLI reference](../docs/cli.md) · [Verified builds](../docs/verified-builds.md)

Run these scripts from the repository root in Linux after installing `ewhb` and preparing the [local source archives](../docs/source-archives.md).
They invoke the public CLI; they do not install system tools or Intel compilers.

| Example | Prerequisites | Validation |
| --- | --- | --- |
| [intel-classic.sh](intel-classic.sh) | Existing classic Intel compilers and Intel MPI | Based on the recorded Intel 2018 route |
| [gnu.sh](gnu.sh) | GCC, GFortran and OpenMPI | Clean end-to-end validation pending |

## Preview First

```bash
bash examples/intel-classic.sh ~/wrf-hydro-packages ~/wrfhydro-intel \
  ~/intel/parallel_studio_xe_2018 --dry-run

bash examples/gnu.sh ~/wrf-hydro-packages ~/wrfhydro-gnu --dry-run
```

Inspect the generated `<prefix>/bootstrap_easy_wrf_hydro.sh`, then rerun the chosen command without `--dry-run` to compile.
Append `--run-example` only when matching Croton data is available. Other bootstrap options, such as `--jobs 2`, can be appended too.

One prefix belongs to one compiler/version combination. The scripts default to four dependency build jobs. The Intel example is not an ifx profile; see the [compiler matrix](../docs/intel-compiler-matrix.md).

The former `intel_wsl2.yaml` was a configuration sketch, not an executable example: the CLI has no YAML loader. These shell scripts replace it.
