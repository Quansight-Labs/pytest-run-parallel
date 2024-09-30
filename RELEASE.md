To release a new version of `pytest-run-parallel`:
1. Update changelog using `git cliff --unreleased --tag vX.X.X`
2. Update version in `pyproject.toml`, remove `-dev` suffix
3. Make release commit using git add -A && git commit -m "chore(release): release vX.X.X"
4. git tag -a vX.X.X -m "Release vX.X.X"
5. Increment minor version and append the `-dev` suffix
6. git add -A && git commit -m "chore: set development version to vY.Y.Y"
7. git push && git push --tags
8. Create a new release in GitHub and wait for package distribution to be
uploaded to PyPi.
