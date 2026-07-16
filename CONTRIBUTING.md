# How to Contribute

<!-- Basic instructions about where to send patches, check out source code, and get development support.-->

We're so thankful you're considering contributing to an [open source project of
the U.S. government](https://code.gov/)! If you're unsure about anything, just
ask -- or submit the issue or pull request anyway. The worst that can happen is
you'll be politely asked to change something. We appreciate all friendly
contributions.

We encourage you to read this project's CONTRIBUTING policy (you are here), its
[LICENSE](LICENSE), and its [README](README.md).

## Getting Started

This project doesn't currently use `good-first-issue` or `easy` labels. If you're new and looking for a place to start, check open issues for anything untriaged, or comment on an issue to ask if it's still relevant before picking it up — this avoids duplicate work.

## Team Specific Guidelines

Our project maintainers are listed in [COMMUNITY.md](COMMUNITY.md). They are responsible for reviewing and merging all pull requests. Feel free to tag them in issues or pull requests if you need input or assistance.

### Building dependencies

This is a Python project. You'll need Python 3.9+ and the packages listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

`openpyxl` is required alongside `pandas` to read the `.xlsx`/`.xls` lookup files used by the pipeline (`pandas.read_excel(..., engine="openpyxl")`).

### Building the Project

There's no compiled build step — this is a set of standalone Python scripts (`makeYaml.py`, `makeCodebook.py`, `makeAll.py`) that are run directly. See the [README](README.md) for usage instructions and sample input files.

### Workflow and Branching

We follow the [GitHub Flow Workflow](https://guides.github.com/introduction/flow/):

1. Fork the project
2. Check out the `main` branch
3. Create a feature branch
4. Write code and tests for your change
5. From your branch, make a pull request against the project's `main` branch
6. Work with repo maintainers to get your change reviewed
7. Wait for your change to be merged into `main`
8. Delete your feature branch

### Testing Conventions

Tests live in `tests/` and are run with:

```bash
pytest tests/
```

Currently, `tests/test_makeYaml.py` covers `makeYaml.py` (file validation, filename parsing, catalog parsing, and codebook construction, using mocked file/Excel reads). `makeCodebook.py` and `makeAll.py` don't yet have dedicated tests — contributions adding coverage for those are welcome. If you add a new function or change existing behavior in any of the three scripts, please add or update a corresponding test in `tests/`.

### Coding Style and Linters

This project enforces code quality and formatting standards using **Ruff**. Our rules—configured in the `pyproject.toml` file at the root of the repository—align with standard [PEP 8](https://peps.python.org/pep-0008/) conventions and match the **Black** code style.

Before committing your changes, please run the following commands in the root of the repository:

**1. Check for lint errors and autofix common issues:**
```bash
ruff check . --fix
```

**2. Format your code to match our styling rules:**
```bash
ruff format .
```

### Writing Issues

When creating an issue, please try to adhere to the following format:

```
module-name: One line summary of the issue (less than 72 characters)

### Expected behavior

As concisely as possible, describe the expected behavior.

### Actual behavior

As concisely as possible, describe the observed behavior.

### Steps to reproduce the behavior

List all relevant steps to reproduce the observed behavior, including the command run and any relevant input file details (e.g. filenames, column names) if the issue is data-related.
```

### Writing Pull Requests

Please keep pull requests focused on a single change. In your PR description, include:

- **Problem** — what you're fixing or adding, and why
- **Solution** — a short description of the change
- **Testing** — how you verified it works (e.g. which tests you ran or added)

Some notes on commit messages:

- Describe what was done, not the result
- Use the active voice and present tense
- Keep the summary line under ~72 characters and don't end it in a period

### Reviewing Pull Requests

Pull requests are reviewed by the project maintainers listed in [COMMUNITY.md](COMMUNITY.md) before merging. Reviewers will check for:

- Correctness — does the change do what it says, without breaking existing behavior
- Test coverage — are new functions/behavior changes accompanied by tests in `tests/`
- Code clarity — does the change follow [PEP 8](https://peps.python.org/pep-0008/) and match the style of surrounding code
- Documentation — is the [README](README.md) updated if the change affects usage, inputs, or outputs
- Scope — is the pull request focused on a single change

Once a pull request is approved, a maintainer will merge it into `main`.

## Shipping Releases

Releases are created by maintainers as needed when significant changes are merged. We use semantic versioning for releases.

## Documentation

Documentation improvements are always welcome, and don't require an issue to be filed first for small fixes (typos, clarifications). For larger documentation changes, please open an issue first to discuss the approach. Key areas for documentation:

- [README.md](README.md) — usage instructions, expected input files, and pipeline behavior
- Docstrings and inline comments in `makeYaml.py`, `makeCodebook.py`, and `makeAll.py`
- Sample catalog/Excel file formats referenced in the README, if their expected structure changes

## Policies

### Open Source Policy

We adhere to the [CMS Open Source
Policy](https://github.com/CMSGov/cms-open-source-policy). If you have any
questions, just [shoot us an email](mailto:opensource@cms.hhs.gov).

### Security and Responsible Disclosure Policy

_Submit a vulnerability:_ Vulnerability reports can be submitted through [Bugcrowd](https://bugcrowd.com/cms-vdp). Reports may be submitted anonymously. If you share contact information, we will acknowledge receipt of your report within 3 business days.

For more information about our Security, Vulnerability, and Responsible Disclosure Policies, see [SECURITY.md](SECURITY.md).

## Public domain

This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/) as indicated in [LICENSE](LICENSE).

All contributions to this project will be released under the CC0 dedication. By submitting a pull request or issue, you are agreeing to comply with this waiver of copyright interest.