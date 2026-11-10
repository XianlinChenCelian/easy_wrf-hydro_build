"""Prepare independent WRF-Hydro parameter experiments from an existing case."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from .atmosphere import sha256


@dataclass(frozen=True)
class Parameter:
    file: str
    variable: str
    units: str
    zero_allowed: bool = False


PARAMETERS = {
    "refkdt": Parameter("soil_properties.nc", "refkdt", "1"),
    "dksat": Parameter("soil_properties.nc", "dksat", "m/s", zero_allowed=True),
    "lksat": Parameter("hydro2dtbl.nc", "LKSAT", "m/s", zero_allowed=True),
    "ov_rough2d": Parameter("hydro2dtbl.nc", "OV_ROUGH2D", "Manning n"),
    "retdeprtfac": Parameter("Fulldom_hires.nc", "RETDEPRTFAC", "1", zero_allowed=True),
    "ovroughrtfac": Parameter("Fulldom_hires.nc", "OVROUGHRTFAC", "1"),
    "lksatfac": Parameter("Fulldom_hires.nc", "LKSATFAC", "1", zero_allowed=True),
    "channel_manning_n": Parameter("Route_Link.nc", "n", "Manning n"),
    "channel_manning_n_compound": Parameter("Route_Link.nc", "nCC", "Manning n"),
    "gw_coefficient": Parameter("GWBUCKPARM.nc", "Coeff", "model coefficient", zero_allowed=True),
    "gw_exponent": Parameter("GWBUCKPARM.nc", "Expon", "1"),
    "gw_max_depth": Parameter("GWBUCKPARM.nc", "Zmax", "mm"),
}


def _case_directory(template: Path, name: str) -> Path:
    matches = [path for path in template.iterdir() if path.name.upper() == name]
    if len(matches) != 1 or not matches[0].is_dir():
        raise ValueError(f"Template {template} needs one readable {name} directory (or symlink).")
    return matches[0]


def _read_changes(config: Path) -> dict:
    def unique_fields(pairs):
        fields = {}
        for key, value in pairs:
            if key in fields:
                raise ValueError(f"Duplicate parameter configuration key: {key!r}.")
            fields[key] = value
        return fields

    return json.loads(config.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)


def _validate_changes(changes):
    if not isinstance(changes, dict):
        raise ValueError("Use a JSON object keyed by parameter name. An empty object makes a baseline copy.")
    for name, change in changes.items():
        if name not in PARAMETERS:
            raise ValueError(f"Unknown parameter {name!r}. Use --list to see the supported parameters.")
        if not isinstance(change, dict) or len(change) != 1 or next(iter(change)) not in {"scale", "set"}:
            raise ValueError(f"{name}: specify exactly one operation, scale or set.")
        operation, value = next(iter(change.items()))
        if (type(value) not in {int, float} or not math.isfinite(value)
                or value < 0 or (value == 0 and not PARAMETERS[name].zero_allowed)):
            bound = "nonnegative" if PARAMETERS[name].zero_allowed else "positive"
            raise ValueError(f"{name}: {operation} must be a finite {bound} number.")


def _slices(shape):
    if not shape or 0 in shape:
        raise ValueError("Expected a nonempty spatial or feature parameter array.")
    axis = max(range(len(shape)), key=shape.__getitem__)
    count = max(1, 1_000_000 // (math.prod(shape) // shape[axis]))
    for start in range(0, shape[axis], count):
        indexes = [slice(None)] * len(shape)
        indexes[axis] = slice(start, start + count)
        yield tuple(indexes)


def _valid_values(values):
    import numpy as np

    raw = np.asarray(values)
    # Older domain products also use the -9999 sentinel without a missing-value attribute.
    valid = ~np.ma.getmaskarray(values) & np.isfinite(raw) & (raw != -9999)
    return raw, valid


def _parameter_values(path: Path, name: str, change: dict | None = None):
    import numpy as np
    from netCDF4 import Dataset, default_fillvals

    spec = PARAMETERS[name]
    if not path.is_file():
        raise ValueError(f"{name}: {spec.file} is missing from the template DOMAIN.")
    with Dataset(path, "r+" if change else "r") as data:
        if spec.variable not in data.variables:
            raise ValueError(f"{name}: {spec.variable} is missing from {spec.file}.")
        variable = data.variables[spec.variable]
        packed = {"scale_factor", "add_offset", "least_significant_digit"}
        if variable.dtype.kind != "f" or packed.intersection(variable.ncattrs()):
            raise ValueError(f"{name}: expected an unpacked floating-point variable in {spec.file}.")
        if name == "gw_max_depth" and (
            "Zinit" not in data.variables or data.variables["Zinit"].dimensions != variable.dimensions
        ):
            raise ValueError("gw_max_depth requires a matching Zinit array in GWBUCKPARM.nc.")
        before = [math.inf, -math.inf]
        after = before.copy()
        count = changed = 0
        if change:
            operation, value = next(iter(change.items()))
            valid_range = getattr(variable, "valid_range", (
                getattr(variable, "valid_min", -math.inf), getattr(variable, "valid_max", math.inf)
            ))
            fill_value = getattr(variable, "_FillValue", default_fillvals[f"f{variable.dtype.itemsize}"])
            missing = np.append(getattr(variable, "missing_value", -9999), fill_value)
        for indexes in _slices(variable.shape):
            raw, valid = _valid_values(variable[indexes])
            old = raw[valid]
            if not old.size:
                continue
            count += old.size
            before = [min(before[0], float(old.min())), max(before[1], float(old.max()))]
            if not change:
                continue
            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                new = old.astype("f8") * value if operation == "scale" else np.full(old.shape, value, dtype="f8")
                new = new.astype(variable.dtype)
            if (not np.isfinite(new).all() or np.any(new < 0)
                    or (not spec.zero_allowed and np.any(new == 0))
                    or np.any(new < valid_range[0]) or np.any(new > valid_range[1])
                    or np.isin(new, missing).any()):
                raise ValueError(f"{name}: adjusted values are outside the valid range of {spec.variable}.")
            if name == "gw_max_depth":
                initial, available = _valid_values(data.variables["Zinit"][indexes])
                if not available[valid].all() or np.any(new < initial[valid]):
                    raise ValueError("gw_max_depth: Zmax must be at least Zinit for each basin.")
            chunk_changes = int(np.count_nonzero(new != old))
            changed += chunk_changes
            after = [min(after[0], float(new.min())), max(after[1], float(new.max()))]
            if chunk_changes:
                updated = raw.copy()
                updated[valid] = new
                variable[indexes] = updated
        if not count:
            raise ValueError(f"{name}: no valid values found in {spec.file}.")
        info = {"file": spec.file, "variable": spec.variable, "units": spec.units,
                "valid_values": int(count), "template_range": before}
        if change:
            info.update(operation=change, result_range=after, changed_values=changed)
        return info


def list_parameters(template: Path) -> dict:
    domain = _case_directory(template, "DOMAIN")
    available = {}
    for name, spec in PARAMETERS.items():
        try:
            available[name] = {"available": True, **_parameter_values(domain / spec.file, name)}
        except (ValueError, OSError) as exc:
            available[name] = {"available": False, "file": spec.file, "variable": spec.variable,
                               "reason": str(exc)}
    return {"template": str(template), "parameters": available}


def prepare_parameters(template: Path, config: Path, output: Path, *,
                       forcing_dir: Path | None = None) -> dict:
    return apply_parameter_changes(template, _read_changes(config), output, forcing_dir=forcing_dir)


def apply_parameter_changes(template: Path, changes: dict, output: Path, *,
                            forcing_dir: Path | None = None) -> dict:
    domain = _case_directory(template, "DOMAIN")
    if forcing_dir is not None and not forcing_dir.is_dir():
        raise ValueError(f"Choose an existing offline forcing directory: {forcing_dir}")
    source = forcing_dir if forcing_dir is not None else _case_directory(template, "FORCING")
    forcing = source.resolve(strict=True)
    # Resolve the parent only so a dangling output symlink cannot bypass the existence check.
    output = output.parent.resolve() / output.name
    if output.exists() or output.is_symlink():
        raise ValueError(f"Choose a new parameter experiment directory: {output}")
    if any(root == output or root in output.parents for root in (domain.resolve(), forcing)):
        raise ValueError("Place the experiment outside the template DOMAIN and the selected forcing directory.")
    _validate_changes(changes)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ewhb-parameters-", dir=output.parent) as temporary:
        staging = Path(temporary) / "case"
        staging.mkdir()
        # Compute the link from its final location, after the staged directory is renamed.
        try:
            link = os.path.relpath(forcing, output)
        except ValueError:  # Native Windows paths on different drives.
            link = str(forcing)
        try:
            (staging / "FORCING").symlink_to(link, target_is_directory=True)
        except OSError as exc:
            raise ValueError("Cannot create the FORCING link. Use APFS or a Linux filesystem for "
                             "--output (under WSL, use your Linux home). The template can stay on "
                             f"its existing drive. {exc}") from exc
        shutil.copytree(domain, staging / "DOMAIN", copy_function=shutil.copyfile,
                        ignore=shutil.ignore_patterns("._*", ".DS_Store"))
        tables = {}
        for folder in (template / "parameter-tables", template):
            if folder.is_dir():
                for entry in folder.glob("*"):
                    if entry.is_file() and entry.suffix.upper() == ".TBL" and not entry.name.startswith("._"):
                        tables[entry.name] = entry
        for name, source in tables.items():
            shutil.copyfile(source, staging / name)
        files = {PARAMETERS[name].file for name in changes}
        provenance = {name: {"template_sha256": sha256(staging / "DOMAIN" / name)}
                      for name in sorted(files) if (staging / "DOMAIN" / name).is_file()}
        edits = {name: _parameter_values(staging / "DOMAIN" / PARAMETERS[name].file, name, change)
                 for name, change in changes.items()}
        for name in provenance:
            provenance[name]["result_sha256"] = sha256(staging / "DOMAIN" / name)
        report = {"template": str(template), "output": str(output), "domain": str(output / "DOMAIN"),
                  "forcing_source": "custom" if forcing_dir is not None else "template",
                  "forcing_target": str(forcing), "forcing_link": link, "edits": edits,
                  "netcdf_files": provenance, "copied_tables": sorted(tables)}
        for name, content in (("parameters.json", changes), ("parameter-manifest.json", report)):
            (staging / name).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        if output.exists() or output.is_symlink():
            raise ValueError(f"Experiment directory appeared during preparation: {output}")
        staging.rename(output)
    return report
