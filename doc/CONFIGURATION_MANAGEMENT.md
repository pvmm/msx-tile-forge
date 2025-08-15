# Configuration Management Plan: MSX Tile Forge

This document outlines the versioning, branching, and release strategy for the MSX Tile Forge project. The process is heavily automated using GitHub Actions.

## 1. Branching Strategy

The repository uses a hierarchical branching model to separate ongoing development from stable releases.

`master` -> `VER_XX` -> `VER_XX.YY` -> `REL_XX.YY.ZZ` -> `TKT_TTTTT`

-   **`master`**: The main branch. Contains only code from official, stable releases.
-   **`VER_XX`**: Major version branches (e.g., `VER_01`). Allows for long-term support or development of a major version while a new major version is in progress.
-   **`VER_XX.YY`**: Minor version branches (e.g., `VER_01.00`).
-   **`REL_XX.YY.ZZ`**: The primary integration branch for a specific patch release (e.g., `REL_01.00.00`). All feature tickets for this release are merged here.
-   **`TKT_TTTTT`**: Feature branches (e.g., `TKT_00011`). Each new feature or bug fix is developed in its own ticket branch, based off the corresponding `REL` branch.

## 2. Versioning Rules

The version string in the source code (`APP_VERSION`) is always set to `<unreleased>`. The official version is dynamically inserted during the build process based on the trigger.

-   **Rule 1: Developer Build**
    -   **Purpose:** Create a private, testable build from a feature branch.
    -   **Version Format:** `vXX.YY.ZZ_devTTTTT.AA_BBBBB`
        -   `XX.YY.ZZ`: Base version from the parent `REL` branch.
        -   `TTTTT`: The GitHub issue number from the branch name.
        -   `AA`: The total commit count on the `TKT` branch (build number for that branch).
        -   `BBBBB`: The unique, global build number from GitHub Actions.
    -   **Output:** Private **Build Artifact** downloadable from the workflow run page.
    -   **Tag:** No git tag is created.

-   **Rule 2: Release Candidate (RC) Build**
    -   **Purpose:** Create a formal, public pre-release for wider testing.
    -   **Version Format:** `vXX.YY.ZZ_rcCC_BBBBB`
        -   `XX.YY.ZZ`: Base version from the `REL` branch.
        -   `CC`: A sequential number (1, 2, 3...) automatically calculated by the workflow.
        -   `BBBBB`: The unique, global build number.
    -   **Output:** Public **Pre-release Asset** on the GitHub Releases page.
    -   **Tag:** A git tag (e.g., `v1.0.0-RC1`) is created and pushed **automatically**.

-   **Rule 3: Final Release Build**
    -   **Purpose:** Create the official, stable release.
    -   **Version Format:** `vXX.YY.ZZ`
    -   **Output:** Public **"Latest" Release Asset** on the GitHub Releases page.
    -   **Tag:** The git tag (e.g., `v1.0.0`) is the **trigger** for this action.
    -   **Post-Release Action:** Automatically creates Pull Requests to merge the release up the branch hierarchy.

-   **Rule 4: Nightly Build**
    -   **Purpose:** Provide a daily "bleeding-edge" build from a designated branch for continuous integration and testing.
    -   **Version Format:** `vXX.YY.ZZ_nightlyYYMMDD_BBBBB`
        -   `YYMMDD`: The date of the build.
    -   **Output:** Public download links posted as a **comment on the latest commit**. Not a formal Release or Artifact.
    -   **Tag:** No git tag is created.

## 3. Developer "Cookbook": How to Trigger Builds

### How to Create a Developer Build (Rule 1)
1.  Work on your feature branch (e.g., `REL_01.00.00/TKT_123_new_feature`).
2.  Commit and `git push` your changes.
3.  Go to the **Actions** tab on the GitHub repository.
4.  Select the **"MSX Tile Forge Build & Release"** workflow.
5.  Click the **"Run workflow"** dropdown.
6.  Ensure your `TKT` branch is selected.
7.  Ensure the "Type of build to run" is set to **`dev_build`**.
8.  Click the green "Run workflow" button.
9.  Wait for the job to complete, then download the artifact from the run's summary page.

### How to Create a Release Candidate (Rule 2)
1.  Ensure all feature branches for the release are merged into the `REL_XX.YY.ZZ` branch.
2.  Go to the **Actions** tab on the GitHub repository.
3.  Select the **"MSX Tile Forge Build & Release"** workflow.
4.  Click the **"Run workflow"** dropdown.
5.  Select the target `REL_XX.YY.ZZ` branch.
6.  Change the "Type of build to run" to **`rc_build`**.
7.  Click the green "Run workflow" button.
8.  The workflow will automatically calculate the next RC number (e.g., RC1, RC2...), create the tag, build, and publish the pre-release.

### How to Create a Final Release (Rule 3)
1.  Ensure the `REL_XX.YY.ZZ` branch is stable and ready.
2.  From your local machine, checkout the branch.
3.  Create and push the final version tag:
    ```bash
    git checkout REL_01.00.00
    git tag v1.0.0
    git push origin v1.0.0
    ```
4.  The push of this tag will automatically trigger the workflow to build and publish the "Latest" release.
5.  After the release, go to the "Pull Requests" tab on GitHub to review and approve the auto-generated PRs for merging back to `master`.

### How to Configure the Nightly Build (Rule 4)
1.  This only needs to be done once per release cycle.
2.  From your local machine, force-update the "pointer tag" to point to the branch you want nightly builds for:
    ```bash
    # Example: Set nightly builds for the v1.0.0 release branch
    git tag -f nightly-build-branch REL_01.00.00
    git push -f origin nightly-build-branch
    ```
3.  The workflow will now automatically check this branch every night.