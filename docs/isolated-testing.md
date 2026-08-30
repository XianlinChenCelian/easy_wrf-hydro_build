# Isolated Full-Loop Testing

Use the isolated runner when validating a release on a machine that already has
working WRF, WPS, or WRF-Hydro installations. The test creates a new prefix and
does not source its environment from `.bashrc`.

## Intel

```bash
bash scripts/linux/run_isolated_full_loop.sh \
  --compiler-family intel \
  --shared-dir /path/to/source-archives \
  --intel-home /path/to/intel \
  --jobs 6
```

## GNU

```bash
bash scripts/linux/run_isolated_full_loop.sh \
  --compiler-family gnu \
  --shared-dir /path/to/source-archives \
  --jobs 6
```

By default, the test prefix is named
`~/ewhb_isolated_full_<family>_<timestamp>`. It is removed after success and
kept after failure so logs can be inspected. Pass `--keep` to preserve a
successful test environment.

The runner rejects prefixes outside `~/ewhb_isolated_full_*` and
`/tmp/ewhb_isolated_full_*`. This guard exists because successful tests perform
recursive cleanup of the selected prefix.
