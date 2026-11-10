"""Render final WRF-Hydro parameter fields as standalone PNG maps."""

from __future__ import annotations

import math
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
from netCDF4 import Dataset

from .parameters import PARAMETERS, _valid_values

MAP_DIRECTORY = "parameter-maps"
DISPLAY_CELLS = 1200
GRID_DIMS = (("south_north", "west_east"), ("y", "x"))


class MapUnavailable(ValueError):
    """The source has no compatible spatial representation for this parameter."""


def _variable(dataset, name):
    if name not in dataset.variables:
        raise MapUnavailable(f"Missing {name} in {Path(dataset.filepath()).name}.")
    return dataset.variables[name]


def _masked(values):
    raw, valid = _valid_values(values)
    return np.ma.array(raw, mask=~valid, copy=False)


def _grid_axis(dataset, dimension, count, attribute):
    coordinate = dataset.variables.get(dimension)
    if coordinate is not None and coordinate.dimensions == (dimension,) and count > 1:
        values = _masked(coordinate[:])
        if values.count() == count:
            steps = np.diff(values.data)
            step = float(steps[0])
            if step and np.allclose(steps, step, rtol=1e-4, atol=0.001):
                bounds = [float(values[0] - step / 2), float(values[-1] + step / 2)]
                unit = str(getattr(coordinate, "units", "")).strip().lower()
                if unit in {"m", "meter", "meters", "metre", "metres"}:
                    return [bound / 1000 for bound in bounds], "km"
    spacing = float(getattr(dataset, attribute, 0))
    if math.isfinite(spacing) and spacing > 0:
        return [0, count * spacing / 1000], "km"
    return [0, count], "cells"


def _grid(dataset, variable):
    dimensions = variable.dimensions
    grid = next((pair for pair in GRID_DIMS if set(pair) <= set(dimensions)), None)
    if grid is None:
        raise MapUnavailable("No recognized horizontal grid dimensions.")
    y, x = grid
    rows, cols = (len(dataset.dimensions[axis]) for axis in grid)
    if not rows or not cols:
        raise MapUnavailable("The grid is empty.")
    stride = max(1, math.ceil(max(rows, cols) / DISPLAY_CELLS))
    layer = next((dim for dim in dimensions if dim.lower() in {"soil_layers_stag", "soil_layers"}), None)
    for dim in dimensions:
        if dim not in (*grid, layer) and len(dataset.dimensions[dim]) != 1:
            raise MapUnavailable(f"Unsupported dimension {dim!r} with more than one entry.")
    layers = len(dataset.dimensions[layer]) if layer else 1
    if not layers:
        raise MapUnavailable("The soil layer dimension is empty.")
    horizontal = [dim for dim in dimensions if dim in grid]
    planes = []
    for index in range(layers):
        key = tuple(slice(None, None, stride) if dim in grid else index if dim == layer else 0
                    for dim in dimensions)
        plane = _masked(variable[key])
        planes.append(plane.T if horizontal == [x, y] else plane)
    xbounds, xunit = _grid_axis(dataset, x, cols, "DX")
    ybounds, yunit = _grid_axis(dataset, y, rows, "DY")
    return planes, {
        "extent": xbounds + ybounds, "stride": stride,
        "xlabel": f"Model x ({xunit})", "ylabel": f"Model y ({yunit})",
        "aspect": "equal" if xunit == yunit else "auto",
        "layers": [f"Soil layer {i + 1}" for i in range(layers)] if layer else [],
    }


def _match(keys, values, targets):
    """Join parameter rows to spatial features by identifier, independent of row order."""
    valid = ~np.ma.getmaskarray(keys) & ~np.ma.getmaskarray(values) & (keys.data > 0)
    ordered = np.argsort(keys.data[valid])
    ids, numbers = keys.data[valid][ordered], values.data[valid][ordered]
    if not ids.size:
        raise MapUnavailable("No valid spatial identifiers for this parameter.")
    if np.any(ids[1:] == ids[:-1]):
        raise MapUnavailable("Parameter identifiers are not unique.")
    position = np.searchsorted(ids, targets.data).clip(0, ids.size - 1)
    missing = np.ma.getmaskarray(targets) | (ids[position] != targets.data)
    return np.ma.array(numbers[position], mask=missing)


def _reach_points(dataset, values):
    lon, lat = (_masked(_variable(dataset, axis)[:]) for axis in ("lon", "lat"))
    if lon.ndim != 1 or lon.shape != lat.shape or lon.shape != values.shape:
        raise MapUnavailable("The parameter and reach coordinates use different shapes.")
    valid = ~(np.ma.getmaskarray(lon) | np.ma.getmaskarray(lat) | np.ma.getmaskarray(values))
    valid &= (abs(lat.data) <= 90) & (abs(lon.data) <= 180)
    return lon.data[valid], lat.data[valid], values.data[valid]


def _groundwater(domain, dataset, variable):
    values = _masked(variable[:])
    basins = domain / "GWBASINS.nc"
    if basins.is_file():
        with Dataset(basins) as geo:
            (basin_grid,), grid = _grid(geo, _variable(geo, "BASIN"))
        ids = _masked(_variable(dataset, "Basin")[:])
        if ids.ndim != 1 or ids.shape != values.shape:
            raise MapUnavailable("The groundwater parameter and basin IDs use different shapes.")
        return "groundwater_basins", [_match(ids, values, basin_grid)], grid

    # Older reach-based cases provide ComID in the bucket table and no land-grid mask.
    routes = domain / "Route_Link.nc"
    if not routes.is_file() or "ComID" not in dataset.variables:
        raise MapUnavailable("No GWBASINS.nc or groundwater ComID / Route_Link.nc locations.")
    ids = _masked(_variable(dataset, "ComID")[:])
    if ids.ndim != 1 or ids.shape != values.shape:
        raise MapUnavailable("The groundwater parameter and outlet IDs use different shapes.")
    with Dataset(routes) as reaches:
        matched = _match(ids, values, _masked(_variable(reaches, "link")[:]))
        points = _reach_points(reaches, matched)
    return "groundwater_outlets", points, {}


def _read_parameter(domain, spec):
    path = domain / spec.file
    if not path.is_file():
        raise MapUnavailable(f"Missing {spec.file}.")
    with Dataset(path) as dataset:
        variable = _variable(dataset, spec.variable)
        if spec.file == "Route_Link.nc":
            return "reach_points", _reach_points(dataset, _masked(variable[:])), {}
        if spec.file == "GWBUCKPARM.nc":
            return _groundwater(domain, dataset, variable)
        planes, grid = _grid(dataset, variable)
        return "raster", planes, grid


def _render(path, name, spec, kind, data, grid):
    descriptions = {
        "raster": "Model grid",
        "reach_points": "River reach locations",
        "groundwater_basins": "Groundwater basin grid",
        "groundwater_outlets": "Groundwater outlet locations (ComID matched to river link)",
    }
    raster = kind in {"raster", "groundwater_basins"}
    valid = [plane.compressed() for plane in data if plane.count()] if raster else [data[2]]
    limits = [(float(values.min()), float(values.max())) for values in valid if values.size]
    if not limits:
        raise MapUnavailable("No valid parameter values at spatial locations.")
    low = min(pair[0] for pair in limits)
    high = max(pair[1] for pair in limits)
    constant = low == high
    count = len(data) if raster else 1
    cols = min(2, count)
    rows = math.ceil(count / cols)
    fig = Figure(figsize=(7.8 if cols == 1 else 10.2, 4.7 if rows == 1 else 3.55 * rows),
                 layout="constrained", facecolor="white")
    FigureCanvasAgg(fig)
    title = descriptions[kind] + f"  |  {spec.file} / {spec.variable}"
    if grid.get("stride", 1) > 1:
        title += f"  |  display samples every {grid['stride']} cells"
    if constant:
        title += f"\nConstant value: {low:.7g} {spec.units}"
    fig.suptitle(f"{name}\n{title}", fontsize=11)
    axes = fig.subplots(rows, cols, squeeze=False).ravel()
    plotted = []
    low_color, high_color = (low, high) if not constant else (low - 1, high + 1)
    style = {"cmap": "viridis", "vmin": low_color, "vmax": high_color}
    if raster:
        labels = grid["layers"] or [""] * count
        for ax, plane, label in zip(axes, data, labels):
            artist = ax.imshow(plane, extent=grid["extent"], origin="lower", interpolation="nearest",
                               aspect=grid["aspect"], **style)
            ax.set_xlim(sorted(grid["extent"][:2]))
            ax.set_ylim(sorted(grid["extent"][2:]))
            ax.set(xlabel=grid["xlabel"], ylabel=grid["ylabel"], title=label)
            if not plane.count():
                ax.text(0.5, 0.5, "No valid cells", transform=ax.transAxes, ha="center")
            plotted.append(ax)
    else:
        lon, lat, values = data
        ax = axes[0]
        artist = ax.scatter(lon, lat, c=values, s=10, linewidths=0, **style)
        ax.set(xlabel="Longitude (degrees east)", ylabel="Latitude (degrees north)",
               aspect=1 / max(0.1, math.cos(math.radians(float(lat.mean())))))
        ax.ticklabel_format(useOffset=False)
        plotted.append(ax)
    for ax in axes[count:]:
        ax.set_visible(False)
    for ax in plotted:
        ax.set_facecolor("#f0f2f4")
        ax.tick_params(labelsize=8)
    if not constant:
        fig.colorbar(artist, ax=plotted, shrink=0.82, pad=0.035, label=spec.units)
    fig.savefig(path, dpi=140)
    fig.clear()
    return {"file": path.name, "kind": kind, "range": [low, high], "units": spec.units,
            "layers": grid.get("layers", []), "stride": grid.get("stride", 1)}


def write_parameter_maps(domain: Path, output: Path) -> dict:
    output.mkdir()
    images, skipped = {}, {}
    for name, spec in PARAMETERS.items():
        try:
            kind, data, grid = _read_parameter(domain, spec)
            images[name] = _render(output / f"{name}.png", name, spec, kind, data, grid)
        except MapUnavailable as exc:
            skipped[name] = str(exc)
    return {"directory": output.name, "images": images, "skipped": skipped}
