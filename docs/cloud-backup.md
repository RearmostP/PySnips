# Manual Google Drive backup (V1)

Settings → Snippets & Data → Cloud backup → Manage opens a modal dialog.
Connect, back up, choose a snapshot, confirm replacement, or disconnect.
All blocking operations run in a Qt worker; successful restore reloads the
snippet screen in process. Upload uses actual resumable-upload progress;
other stages use an indeterminate indicator. Dates are shown in local time.

## Snapshot contract

**Settings are NOT backed up in V1.** The only authoritative input is
`DATA_DIR/user_data/snips/` and `DATA_DIR/user_data/trash/snips/`.
`PYSNIPS_DATA_DIR` is respected. UTF-8 Markdown, metadata/UUIDs,
categories, deleted snippets and binary media are copied without rewriting.

The portable ZIP looks like this:

```text
manifest.json
snips/
  categories.json
  <category>/<snippet>/metadata.json
  <category>/<snippet>/snippet.md
  <category>/<snippet>/media/...
trash/snips/
  <deleted-snippet>/metadata.json
  <deleted-snippet>/snippet.md
  <deleted-snippet>/media/...
```

`manifest.json` contains `format_version: 1`, a UTC ISO `created_at`, and
the unchanged current `pysnips_version`. Format and application versions are
independent. Filenames use a filesystem-safe UTC timestamp with microseconds:
`PySnips-Backup-2026-10-10T22-30-00-123456Z.zip`.

Settings, cache/search_index, system_data/version.json, updater files,
OAuth client configuration/tokens and hidden atomic-write/staging files
are excluded. Symlinks, junctions and other reparse points (including in
ancestors) are rejected before traversal. A ZIP is built and validated in
a temporary directory before its final filename is published.

## Restore and safety

Restore **replaces** both active and deleted snippets. There is no merge.
An explicit confirmation says that settings remain unchanged.

The ZIP is downloaded to a temporary local filename, inspected before
extraction, then extracted and validated in staging on the data volume.
Validation rejects traversal, absolute/Windows paths, link entries,
duplicate/case-colliding paths, encrypted entries, unexpected top-level
data, missing or invalid manifests, unsupported format versions, missing
categories, invalid UTF-8/metadata and UUID duplication. Existing snippet
readers validate active and deleted snippets. Category and snippet folders
must have the expected layout. Unlisted category directories are also preserved
and validated, matching the existing library's tolerance for those directories;
`categories.json` is not rewritten. Limits: 100,000 entries and 10 GiB uncompressed.

Only then are existing trees renamed aside and the new trees installed.
Search indexing runs before old copies are removed. A caught install or
index error rolls the old library back. A failed rollback retains old data
under `user_data/backup-recovery-*`; close PySnips and recover the
`old-snips`/`old-trash` trees to their original paths before further edits.
A successfully recovered tree may already be back at its original path.
Cleanup errors can leave a hidden `.restore-*` directory for later removal.
The derived search index will be rebuilt on the next search if a rollback
left it out of date. Settings are never replaced.

The dialog prevents concurrent UI edits while operations run and cannot be
closed during a worker operation. The core requires its caller to exclude
concurrent writers. Only one application instance is supported, consistent
with the current library. External editors/other instances must stay closed.
Rollback is exception-safe, not a power-loss/process-kill transaction across
two directories. ZIPs are not encrypted; protect your Google account.

## Google Drive and credentials

The provider is separate from archive/restore logic, with connect, resume,
disconnect, upload, list and download methods. No provider registry is needed.
It creates a normal visible `PySnips Backups` folder directly in My Drive and
marks it with `appProperties.pysnipsBackup = v1`. Subsequent uses of the same
OAuth application reuse that managed folder. A manually created folder with
the same name is not adopted. Uploads also carry this marker. Lists are
paginated, filtered to managed ZIPs, and sorted newest first. Changing OAuth
applications can make previous app-owned files inaccessible with this scope.

Only `https://www.googleapis.com/auth/drive.file` is requested. This provides
access to files created/used with this application, without full Drive access:
[Google scope documentation](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).
No `appDataFolder` is used. Authentication uses a desktop installed-app OAuth
flow with a browser and ephemeral localhost callback port (180-second timeout):
[Google installed-app documentation](https://developers.google.com/identity/protocols/oauth2/native-app).

Tokens are stored only in the OS keyring, under service `PySnips.GoogleDrive`,
account `desktop-oauth-v1`. Windows uses Credential Manager through keyring's
Windows backend. Only Windows/macOS/SecretService OS backends are accepted;
there is no plaintext fallback. Connection resumes and refreshes credentials
when required. All data directories share this OS-user connection. Disconnect
deletes the local credential, including expired credentials; it does not delete
backups or revoke server-side consent. Google Account → third-party connections
can revoke consent separately. Error messages use localization keys and do
not print API responses, client secrets or tokens.

## Developer configuration and first real smoke test

There is no production OAuth client bundled in the repository.
Do not paste client secrets or tokens into chat or commit them.

1. Open Google Cloud Console and create/select a project dedicated to PySnips.
2. Enable **Google Drive API** in APIs & Services → Library.
3. Configure Google Auth Platform branding/audience/data access. For a personal
   external test, keep the app in Testing and add your Google account as a test
   user. Request only `https://www.googleapis.com/auth/drive.file`. Do not add
   full Drive, Gmail, or other scopes. Publishing may require completing
   Google's current consent-screen/verification requirements.
4. In Clients, create an OAuth client with application type **Desktop app**.
   Download its JSON. This is application configuration, not user credentials.
   Do not use a web application or service-account JSON.
5. Store the JSON outside the repository, for example
   `C:\Users\David\AppData\Local\PySnipsDev\google-desktop-client.json`.
6. From the repository root in PowerShell, launch with isolated test data:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   $env:PYSNIPS_GOOGLE_CLIENT_JSON = "$env:LOCALAPPDATA\PySnipsDev\google-desktop-client.json"
   $env:PYSNIPS_DATA_DIR = "$env:TEMP\PySnips-drive-smoke"
   New-Item -ItemType Directory -Force "$env:PYSNIPS_DATA_DIR\system_data" | Out-Null
   Copy-Item .\data\system_data\version.json "$env:PYSNIPS_DATA_DIR\system_data\version.json"
   python main.py
   ```

   The directory above must be a dedicated test library, never your real library.
   The version file is not backed up. In source mode an isolated `DATA_DIR`
   also redirects `SYSTEM_DATA_DIR`, so the commands above copy the version
   resource before launching.
7. Create test snippets with Hebrew content and a media attachment; delete
   another test snippet to populate trash. Open Settings → Manage → Connect.
   The browser should show Google's sign-in and the configured app's consent
   screen. A test/unverified-app message may appear depending on your Cloud
   configuration. Cancellation/timeouts should return an error without
   freezing PySnips; wait for the 180-second timeout if the browser is closed.
8. Check consent details: the Drive permission must be restricted to specific
   files used with this app. It must not say access to all Drive files. You can
   also verify `SCOPES` in `core/backup/google_drive.py` and the project's
   Data Access configuration. See Google's exact scope descriptions above.
9. Click Backup now. Verify real upload progress/success and a newest-first row
   with date/size. In drive.google.com → My Drive, verify `PySnips Backups`
   contains the new ZIP. Download a copy with Drive and inspect its three
   expected roots; confirm settings/tokens are absent.
10. For a safe restore test, remain in the isolated test data directory. Change
    a snippet, add another, and alter an app setting. Select the original
    backup and Restore. First decline confirmation and verify nothing changes.
    Then confirm: original content/media/UUIDs and trash must return, the extra
    snippet must disappear, settings must keep their new value, and search must
    reflect the original snapshot immediately without restarting.
11. Close/reopen to verify keyring resume; Disconnect should require login again.
    If needed, revoke the app in Google Account and check the authorization error.
    Remove the two environment overrides when returning to normal development:

    ```powershell
    Remove-Item Env:PYSNIPS_DATA_DIR
    Remove-Item Env:PYSNIPS_GOOGLE_CLIENT_JSON
    ```

Source development honors `PYSNIPS_GOOGLE_CLIENT_JSON`. Without an override,
the resource path is `assets/oauth/google-desktop-client.json`, relative to
`RESOURCE_ROOT` (including PyInstaller's `_MEIPASS`). This optional JSON is
ignored by Git and included by the existing assets resource collection when
provided at build time. Only bundle the application's desktop client config,
never an authorized-user/token JSON. An absent/invalid config gives a localized
configuration error when connecting, not an application startup crash.

The PyInstaller spec collects Google static discovery documents and keyring
backends, including Windows. No separate Google installation is needed.
The installer and app version are unchanged. Build normally with
`python -m PyInstaller --clean --noconfirm PySnips.spec` after installing
`requirements-build.txt` (which includes the runtime requirements).

## Limits and verification

V1 is manual Google Drive backup/restore only: no settings backup, scheduling,
sync, merge, deletion/retention, quota UI or alternative cloud providers.
There is no real OAuth smoke test until a developer supplies a client config.
Automated tests mock OAuth/Drive/keyring and do not use a Google account.

```powershell
python -m unittest discover -s tests -v
git diff --check
```
