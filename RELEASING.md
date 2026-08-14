# Releasing gpu_stack

This document describes how to cut a release. The short version: you bump the version, tag the commit, and push the tag. CI does the building and publishing. Everything below is the detail behind that sentence.

## Prerequisites (one-time setup)

These steps happen once, before the first release. They let GitHub Actions publish to PyPI without anyone handling an API token.

1. Create the project on PyPI at https://pypi.org/manage/projects/ using the
   name `gpu_stack`.

2. Configure a Trusted Publisher on PyPI (no API token required):
   - Go to your PyPI project > Publishing > Add a new publisher
   - Provider: GitHub Actions
   - Repository owner: your GitHub org or username
   - Repository name: `gpu_stack-`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

3. Create a GitHub environment named `pypi` in the repository settings
   (Settings > Environments). Restrict deployments to tag patterns or add a
   required reviewer to prevent accidental publishes.

## Cutting a release

1. Update the version in `pyproject.toml` (`version = "X.Y.Z"`).

2. Update `CHANGELOG.md` with the new version heading and release notes.

3. Commit both files:
   ```
   git add pyproject.toml CHANGELOG.md
   git commit -m "Release vX.Y.Z"
   ```

4. Tag the commit and push both the commit and the tag:
   ```
   git tag vX.Y.Z
   git push origin main
   git push origin vX.Y.Z
   ```

## What CI does on a version tag

When a `v*` tag is pushed, `.github/workflows/release.yml` runs two jobs in
sequence:

- **build**: installs `build` and `twine`, runs `python -m build` to produce
  an sdist and a wheel, runs `twine check dist/*` to validate metadata, and
  uploads the artifacts to the workflow run.

- **publish**: downloads the artifacts and publishes them to PyPI using
  `pypa/gh-action-pypi-publish` via OIDC trusted publishing. This job requires
  the `pypi` GitHub environment to exist and will only run when the ref is a
  version tag. The one-time PyPI and GitHub setup described above must be
  completed before this job can succeed.

## Building locally (optional)

You do not need this for a normal release, but it is the fastest way to check that the package builds before tagging:

```
pip install -e ".[release]"
python -m build
twine check dist/*
```
