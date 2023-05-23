# update-wrapdb-action

A set of scripts + composite action to update a wrapdb project from a github release.
In the future this repository will also contain a bot that will automatically update registered projects.

## Disclaimer
At the moment this action is not yet published to the marketplace.
It also doesn't open the PR yet

This can only update existing projects to a new version.
All that is done is to update the wrap file and the releases.json file.
In the releases.json file the new version is added to the list of versions and no other change is made.
This means that no new dependencies can be added and no existing dependencies can be removed.
This will be implemented in the future.

## Actions Usage

### Inputs

#### `source-repository`

**Required** The repository which has a new release.

#### `project-name`

**Optional** An override for the project name.
By default, the repository name is used as the project name.
However, this can be overridden by this input in case they differ.

#### `release-tag`

**Required** The tag of the release to update from.
At the moment the version is derived from this.
If tag has a `v` prefix, it will be removed.
Any suffixes will be removed as well (e.g. `v1.0.0-rc1` will become `1.0.0`).
Make sure to only use this action on final releases not pre-releases.

#### `provides`

**Required** The dependencies provided by this project.
This is a comma separated list of dependencies.
They will be split and directly pasted into the wrap file.
The sanity checks will fail if the provided dependencies do not match the ones in the releases.json file.

#### `push-repository`

**Required** The repository to push the changes to.
This is also the repository that will be used to open the PR.

#### `github_token`

**Required** The github token to use to push the changes and open the PR.
Make sure it has write access to the push-repository, read access to the source-repository and the ability to open PRs.

### Example usage

```yaml
on:
  release:
    types: [published]

jobs:
  update-wrapdb:
    runs-on: ubuntu-latest
    name: Update wrapdb
    steps:
    - name: Checkout
      uses: actions/checkout@v2
    - name: Update wrapdb
      uses: noah1510/update-wrapdb-action@latest
      with:
        source-repository: "https://github.com/noah1510/unit-system"
        release-tag: ${{ github.ref }}
        provides: "unit-system = unit_system_dep"
        push-repository: "https://github.com/noah1510/wrapdb"
        github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Python Usage

Before you run the python script, make sure to have the dependencies installed and be authenticated with github.

### Setup

Use pipenv to install the dependencies.
Check out the [pipenv documentation](https://pipenv.pypa.io/en/latest/index.html) for more information.

### Command Line Options

#### `--url` || `-u`

Same as `source-repository` in the action.

#### `--name` || `-n`

Same as `project-name` in the action.

#### `--tag` || `-t`

Same as `release-tag` in the action.

#### `--provides` || `-p`

Same as `provides` in the action.

#### `--push-url`

Same as `push-repository` in the action.

### Example usage

```bash
python3 ./update_repo.py \
    --url 'https://github.com/noah1510/unit-system' \
    --tag 'v0.7.0' \
    --provides 'unit-system = unit_system_dep' \
    --push-url 'https://github.com/noah1510/wrapdb'
```
