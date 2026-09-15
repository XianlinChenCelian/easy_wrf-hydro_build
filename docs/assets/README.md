# Documentation Artwork

[Documentation](../index.md) · [Repository layout](../repository-layout.md)

| Location | Contents |
| --- | --- |
| `brand/logo.png` | Project mark: cloud, rainfall, watershed, river and model grid |
| `brand/social-preview.png` | 1280 x 640 GitHub social preview |
| `figures/build-workflow.png` | README workflow, with a solid white background for light/dark themes |
| `figures/build-workflow.svg` | Self-contained high-resolution figure with embedded assets |
| `figures/watershed.jpg` | Optimized conceptual watershed illustration |
| `source/` | Editable SVG layouts and the full-resolution logo master |

`../ewhb_architecture.svg` remains as a generated compatibility copy for links to the original figure. New documents should use the paths above.

## Design and Provenance

The original graphics use a white background, restrained green/blue toolchain colors, consistent type sizes and numbered stages. The watershed connects the build workflow with its hydrological subject. The figure's validation strip reports the project's actual evidence rather than implying that every route has passed a full run.

The watershed and logo were created with OpenAI's built-in image generation tool and reviewed for this project. The watershed is **not a real terrain dataset, Croton map or simulated output**. Only format conversion and size optimization were applied after generation. Figure labels and workflow connections remain editable SVG. The logo master is a raster image, not an editable vector.

Generation prompt:

> Publication-quality scientific illustration of a hydrological watershed; white background, isometric terrain cutaway, branching tributaries converging into one river, forested hills, rocky ridges, cultivated fields, exposed soil layers, and a numerical-model grid on part of the land surface. Muted green, turquoise, grey and terracotta. No text, arrows, charts, people or logos. A conceptual basin, not Croton NY or a simulation result.

Logo brief and final edit:

> Original water-drop emblem enclosing a mountain watershed, a winding blue river, tributaries, layered green/teal hills and a small model grid. Preserve the approved design and add one cloud with three rainfall marks in the upper sky. Solid pure white background, crisp edges, no lettering, code brackets or cogwheels. Review at small size.

Design references: [easy_vic_build](https://github.com/XudongZhengSteven/easy_vic_build), [HydroMT's workflow figures](https://deltares.github.io/hydromt/stable/user_guide/overview/hydromt_intro.html) and [WRF-Hydro's input-component figure](https://wrf-hydro.readthedocs.io/en/latest/model-inputs-preproc.html). No graphics from those projects are included in this repository.

## Regenerating Figures

Edit the SVG files under `source/`. The script sizes `source/logo-master.png` for use as `brand/logo.png`; `{{LOGO_URI}}` and `{{WATERSHED_URI}}` embed the logo and `figures/watershed.jpg` into the exported figures. Node.js and `sharp` are development-only dependencies; users installing `ewhb` do not need them.

Example on Linux, from the repository root:

```bash
npm install --prefix /tmp/ewhb-art-tools sharp
NODE_PATH=/tmp/ewhb-art-tools/node_modules node scripts/dev/render_assets.mjs
```

The script exports self-contained SVG and PNG files. Review both the full-size result and the image as it appears inside the README before committing.
Set `brand/social-preview.png` in GitHub repository Settings to use it for link previews; committing the file alone does not change that setting.
