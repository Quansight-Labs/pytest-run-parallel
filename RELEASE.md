To release a new version of `pytest-run-parallel`:
1. Update version in `pyproject.toml`, remove `-dev` suffix
2. Make release commit using git add -A && git commit -m "chore(release): release vX.X.X"
3. git tag -a vX.X.X -m "Release vX.X.X"
4. Increment minor version and append the `-dev` suffix
5. git add -A && git commit -m "chore: set development version to vY.Y.Y"
6. git push && git push --tags
7. Create a new release in GitHub and wait for package distribution to be
uploaded to PyPi.
