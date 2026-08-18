# amstack

`amstack` is the Spack package repository for software in the Ambhora GitHub organization.

It is a Spack Package API v2 repository and is intended to be consumed directly as a Git-backed
package repository. Projects can therefore reference `amstack` from their own `spack.yaml` without
requiring users to run `spack repo add` first.

## Repository layout

```text
.
├── amstack.yaml
├── pyproject.toml
├── src/amstack
├── spack-repo-index.yaml
└── spack_repo
    └── amstack
        ├── build_systems
        │   └── ambhora_cmake.py
        ├── repo.yaml
        └── packages
```

`AmbhoraCMakePackage` contains the common Spack-to-BESA CMake translation for Ambhora C++ packages. Generated package recipes therefore contain package metadata, variants, and dependencies but do not duplicate BESA's CMake invocation policy.

## CLI

Run the repository tooling with `uv`:

```bash
uv run amstack --help
```

### Generating C++ package recipes

BESA-generated C++ repositories contain a local `<project>-dev-env` package. That package is a development description, not the package that amstack publishes.

Repositories to analyse are declared in `amstack.yaml`:

```yaml
repositories:
  - url: https://github.com/ambhora/nola.git
```

Every Git tag is discovered automatically. The `main` branch is always exposed as a development version. Additional branches can be requested explicitly:

```yaml
repositories:
  - url: https://github.com/ambhora/nola.git
    branches:
      - develop
      - release/next
```

Configured branches extend `main`; they do not replace it.

Then run:

```bash
uv run amstack sync
```

For each repository, `amstack`:

1. clones the Git repository with its tags and remote branches;
2. discovers every tag and resolves it to its full commit SHA;
3. verifies `main` and any additional configured branches;
4. analyses the BESA-generated `<project>-dev-env` recipe on `main`;
5. analyses the project's declarative BESA CMake feature and dependency declarations;
6. creates a new installable package recipe inheriting `AmbhoraCMakePackage`; and
7. writes it to `spack_repo/amstack/packages/<project>/package.py`.

For example, Git refs may generate:

```python
version("main", branch="main")
version("develop", branch="develop")
version("1.2.0", tag="v1.2.0", commit="<full commit SHA>")
version("1.1.0", tag="v1.1.0", commit="<full commit SHA>")
```

Tags are pinned to the commit they currently resolve to. Branches intentionally remain moving development versions.

For example, `nola-dev-env` is an input to generation, but the output is `nola`:

```text
nola/spack/.../nola_dev_env/package.py
              +
nola/CMakeLists.txt
              |
              v
       amstack sync
              |
              v
amstack/spack_repo/amstack/packages/nola/package.py
```

The development recipe is never copied into amstack.


## Using amstack from a Spack environment

A project's `spack.yaml` can reference this repository directly:

```yaml
spack:
  repos:
    amstack:
      git: https://github.com/ambhora/amstack.git
      branch: main

  specs:
    - <project>
```

Spack will clone the Git-backed package repository automatically when the environment is used.

## Packages

### BESA

BESA is available as the `besa` package. Stable releases are fetched from PyPI, while the package also declares the upstream Git repository for Git-based development versions.

```bash
spack install besa
```

To build directly from the upstream `main` branch:

```bash
spack install besa@git.main
```
