To release a new version of `pytest-run-parallel`:
1. Update version in `pyproject.toml`, remove `-dev` suffix
1. Make release commit using git add -A && git commit -m "chore(release): release vX.X.X"
1. git tag -a vX.X.X -m "Release vX.X.X"
1. Increment minor version and append the `-dev` suffix
1. git add -A && git commit -m "chore: set development version to vY.Y.Y"
1. git push && git push --tags
1. Create a new release in GitHub and wait for package distribution to be
uploaded to PyPi.
