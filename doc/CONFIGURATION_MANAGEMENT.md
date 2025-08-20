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

## 2. Versioning, Builds, and Outputs

The version string in the source code (`APP_VERSION`) is always set to `<unreleased>`. The official version is dynamically inserted during the build process based on the triggered workflow.

-   **Rule 1: Developer Build (`dev-build.yml`)**
    -   **Purpose:** Create a private, temporary build from a feature branch for isolated testing.
    -   **Trigger:** Manual `workflow_dispatch` on a `TKT_TTTTT` branch.
    -   **Version Format:** `XX.YY.ZZ_devTTTTT.AA_BBBBB`
        -   `XX.YY.ZZ`: Base version from the issue's milestone (e.g., `REL_01.00.00`).
        -   `TTTTT`: The GitHub issue number from the branch name.
        -   `AA`: The total commit count on the `TKT` branch.
        -   `BBBBB`: The unique, repository-wide run number from GitHub Actions.
    -   **Output:** Private **Build Artifacts** downloadable only from the workflow run's summary page. Not a public release.
    -   **Tag:** No git tag is created.

-   **Rule 2: Release Candidate Build (`rc-build.yml`)**
    -   **Purpose:** Create a formal, public pre-release for wider testing and integration.
    -   **Trigger:** Manual `workflow_dispatch` on a `REL_XX.YY.ZZ` branch.
    -   **Version Format:** `XX.YY.ZZ_rcCC_BBBBB`
        -   `XX.YY.ZZ`: Base version from the `REL` branch name.
        -   `CC`: A sequential number (1, 2, 3...) automatically calculated based on existing tags.
        -   `BBBBB`: The unique, repository-wide run number.
    -   **Output:** A formal **Pre-release** on the GitHub Releases page, with all packages uploaded as permanent assets.
    -   **Tag:** A git tag (e.g., `v01.00.00_rc1_45`) is created and pushed automatically by the workflow.

-   **Rule 3: Final Release Build (`release.yml`)**
    -   **Purpose:** To build and publish the official, stable release of the software.
    -   **Trigger:** The manual push of a new, clean version tag (e.g., `v01.00.00`) to the repository.
    -   **Version Format:** `XX.YY.ZZ` (parsed directly from the tag).
    -   **Output:** A formal **"Latest" Release** on the GitHub Releases page, with all packages uploaded as permanent assets.
    -   **Tag:** The git tag is the trigger for this action.
    -   *(Future Work):* Post-release action to automatically create Pull Requests for merging up the branch hierarchy.

-   **Rule 4: Nightly Build (`nightly-build.yml`)**
    -   **Purpose:** Provide a daily "bleeding-edge" build from any `REL_XX.YY.ZZ` branch that has had recent activity.
    -   **Trigger:** Automatic nightly schedule (`cron`).
    -   **Version Format:** `XX.YY.ZZ_nightlyYYMMDD_BBBBB`
        -   `XX.YY.ZZ`: Base version from the `REL` branch name being built.
        -   `YYMMDD`: The date of the build.
        -   `BBBBB`: The unique, repository-wide run number.
    -   **Output & Publishing Process:**
        1.  A new, unique **Item** is created on the Internet Archive with a date-stamped identifier (e.g., `msxtileforge_01.00.00_nightly250819_33_all`).
        2.  All built packages (Windows, Linux, Debian, Source) are uploaded as **Files** into this new Item.
        3.  The Item is automatically tagged with the subject metadata `msxtileforge_nightly_build`. This allows all nightly builds to be grouped in a dynamic collection.
        4.  A link to the new Item's page is posted as a **comment on the latest commit** of the built branch.
    -   **How to Find:** All nightly builds can be found at this permanent search URL: **[https://archive.org/search.php?query=subject:"msxtileforge_nightly_build"](https://archive.org/search.php?query=subject:"msxtileforge_nightly_build")**
    -   **Tag:** No git tag is created.

## 3. Developer Cookbook: How to Trigger Builds

All manual builds are triggered from the **Actions** tab on the GitHub repository.

### How to Create a Developer Build
1.  Ensure all your work is committed and pushed to your feature branch (e.g., `TKT_00011`).
2.  Go to the **Actions** tab on GitHub.
3.  Select the **"Developer Build"** workflow from the list.
4.  Click the **"Run workflow"** dropdown button.
5.  Select your `TKT_TTTTT` branch.
6.  Click the green **"Run workflow"** button.
7.  Once the build is complete, you can download the `.zip`, `.tar.gz`, and `.deb` artifacts from the workflow run's summary page.

### How to Create a Release Candidate
1.  Ensure all feature branches for the release have been merged into the target `REL_XX.YY.ZZ` branch (e.g., `REL_01.00.00`).
2.  Go to the **Actions** tab on GitHub.
3.  Select the **"Release Candidate Build"** workflow from the list.
4.  Click the **"Run workflow"** dropdown button.
5.  Select the target `REL_XX.YY.ZZ` branch.
6.  Click the green **"Run workflow"** button.
7.  The workflow will automatically calculate the next RC number, build all packages, create a formal Pre-release on the GitHub Releases page with the packages attached, and push the corresponding Git tag.

### How to Create a Final Release
1.  Ensure the `REL_XX.YY.ZZ` branch for the release is stable, tested, and ready for production.
2.  Merge the release branch up through the hierarchy, pushing each branch to the remote after its update. For example, for version `01.00.00`:
    *   Merge `REL_01.00.00` into `VER_01.00` and push.
    *   Merge `VER_01.00` into `VER_01` and push.
    *   Merge `VER_01` into `master` and push.
3.  From your local machine, check out the now-updated `master` branch.
4.  Create and push the final, clean version tag:
    ```bash
    git checkout master
    git pull
    git tag v01.00.00
    git push origin v01.00.00
    ```
5.  The push of this new tag will automatically trigger the **"Final Release"** workflow, which builds all packages and publishes them to a new "Latest" release on the GitHub Releases page.

### How to Configure the Nightly Build
The nightly build process is fully automatic. It requires no manual configuration. Every night, the system will automatically check all `REL_XX.YY.ZZ` branches for new commits and will trigger a build for any branch that has been updated.