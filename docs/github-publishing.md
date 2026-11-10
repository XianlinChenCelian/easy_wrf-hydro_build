# GitHub Publishing

The repository describes WRF-Hydro builds, basin preparation, forcing conversion, and parameter experiments. Keep the English and Chinese project overviews aligned with the [documentation index](index.md) and [validated configurations](verified-builds.md).

## Source publication

Update the [software citation](../CITATION.cff), the package metadata, and the [changelog](../CHANGELOG.md) for a tagged version. Run `python -m pytest`, `python scripts/dev/check_docs.py`, and `python -m build` on the source tree. State the operating system, compiler, model version, and case for each run reported in the release notes.

## Release assets

Organize build recipes by platform, compiler, and model version. Give each distributable archive a SHA-256 checksum, a source manifest, and the relevant license notices. Link to the vendor for Intel toolchains. The [platform and package guide](release-bundles.md) describes how to assemble packages from upstream materials.

Use `docs/assets/brand/social-preview.png` as the repository social image. The [artwork guide](assets/README.md) lists source files for the project logo and build diagram.
