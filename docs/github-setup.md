# Create the GitHub repository

Suggested repository name: **`pft-rso-detection`**.

Suggested description:

> Standalone PFT/ModifiedPFT detection and tracking of moving-object candidates in optical image sequences, associated with the SpaceOps 2025 ORBIT paper.

Suggested topics: `space-situational-awareness`, `rso-detection`, `tracking`,
`astronomy`, `computer-vision`, `python`.

## 1. Prepare a local checkout

Extract the prepared source archive and open a terminal inside its
`pft-rso-detection` directory. If you received an existing Git checkout, skip the
initialization command.

```bash
git init -b main
python -m pip install -e .
python -m unittest discover -s tests -v
git add .
python tools/check_repository.py
git diff --cached --stat
git commit -m "Package and document the ModifiedPFT detector"
```

Use your normal Git author configuration. Stage and audit the extracted source
directory, not the original uploaded archive. The latter contains input images
and data that do not belong in the repository.

## 2. Create and push with GitHub CLI

If GitHub CLI is installed and authenticated:

```bash
gh repo create pft-rso-detection --private --source . --remote origin --push
```

This creates a private repository for initial review. After checking authorship,
license selection, and the source changes, set the visibility you want through
GitHub's repository settings. Repository creation should not initialize another
README or license because the local checkout already contains the prepared files.

If the repository already exists, do not run `gh repo create` again. Use its
verified remote URL and push the local branch instead.

## 3. Alternative: create an empty repository in the browser

Open [GitHub's new repository page](https://github.com/new), select the intended
account, enter the repository name, and choose the desired visibility. Leave the
README, `.gitignore`, and license initialization options off. Copy the new
repository's HTTPS or SSH URL, then run:

```bash
git remote add origin YOUR_NEW_REPOSITORY_URL
git push -u origin main
```

Replace `YOUR_NEW_REPOSITORY_URL` with the URL GitHub actually gives you. If an
`origin` remote already exists, inspect it with `git remote -v` before changing it.

## Repository contents

The publication contains several ORBIT components outside this source release.
Use the detector-focused name and description above so visitors know the scope.
The `README.md`, `CITATION.cff`, algorithm guide, usage guide, and tests are already
prepared. No GitHub Pages site or web backend is required.

The local `.gitignore` and staged-file check exclude images and data. GitHub
Actions also checks tracked files, but it runs after a push; always run the local
check before pushing. Adding a dataset through a force-add would otherwise bypass
ignore rules.

No software license was included with the original source. Select one with the
appropriate rights holders before distributing the code under a reuse license.
No license is silently assigned by this preparation.

Official references:

- [Creating a new repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
- [GitHub CLI: `gh repo create`](https://cli.github.com/manual/gh_repo_create)
- [Ignoring files](https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files)

