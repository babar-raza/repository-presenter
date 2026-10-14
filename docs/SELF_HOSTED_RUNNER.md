# Self-Hosted Seal Runner

Status: operational runbook, prepared 2026-10-12 for owner decision **D5** (2026-10-11: production
sealing runs on a self-hosted runner on the owner's machine, which has every toolchain and is the
environment the sealed bundles record: Windows, Python 3.13.2). It **enables nothing**: no runner is
registered, no variable or secret is set, nothing is written outside this repository by anything in it.
Every step that changes the machine or GitHub is an owner action (section 7).
Owns: how the seal pipeline chooses its runner, what the runner is and how it is set up on this
machine, what it can and cannot be trusted with, how to switch to it and back, and the residual risk of
running upstream code on the owner's machine.
Does not own: the hosted workflows' behaviour (`docs/OPERATIONS_RUNBOOK.md`), credential rotation
(`docs/CREDENTIAL_ROTATION_RUNBOOK.md`), or the threat analysis of the pipeline itself
(`docs/THREAT_MODEL.md`); it points at them.

## 1. What changes, and what does not

The seal pipeline is `present.yml` (one job per repository, called once per drifted repository by
`sealing-scheduled.yml` or dispatched by hand). The repository variable
`REPOSITORY_PRESENTER_SEAL_RUNNER` chooses where that one job runs:

| Value | Where `present.yml` runs |
|---|---|
| unset, empty, `ubuntu-latest` | a GitHub-hosted `ubuntu-latest` runner, exactly as before (the default) |
| `self-hosted-windows` | the registered runner carrying `self-hosted`, `windows`, `x64`, `repository-presenter-seal` |
| anything else | the run fails closed in `select-runner`, before any runner is asked for |

Nothing else moves. `monitor.yml`, the `plan` job of `sealing-scheduled.yml`, `candidates-publish.yml`,
`propose.yml`, `issues-scheduled.yml` and every other workflow stay hosted, and no other workflow can
name the self-hosted labels (`tests/test_present_runner_selection.py`). The gateway key and the App
secrets already reach `present.yml` only; with the variable set they reach the runner machine only
inside that job.

How a self-hosted seal differs from a hosted one (the workflow is the same file; steps are chosen by
`runner.environment`):

| | Hosted (default) | Self-hosted |
|---|---|---|
| Decision | `select-runner` (always hosted, no secret) | the same job, same output |
| Trigger allowed | any trigger `present.yml` has | schedule, workflow_dispatch, repository_dispatch **on the default branch** only; a `workflow_call` carries its caller's event, so a pull-request caller is refused |
| Presenter interpreter | `setup-python` 3.11 | the pinned `D:\Python313\python.exe` (3.13.2), a fresh venv per job from the lock |
| Toolchains | installed by the workflow (uv, dotnet, java, node, tsc, go, rust, apt) | none installed; the machine's own, resolved by `core/toolchains.py`, verified read-only by `tools/runner/check_runner.py --job` before any provider call |
| Shell | `bash -e {0}` (GitHub's Linux default) | Git for Windows' `bash` |
| Workspace | a fresh VM | emptied first, emptied last, whatever happened |
| Timeout | GitHub's default (360 minutes) | 120 minutes |
| Concurrency | the `present-<repo>` group, never cancelled mid-transaction | the same group; the one runner takes one job at a time, so seals are serial and a second one waits |

Why the environment matters: each bundle records `python_version`, `os`, the presenter's package set and
the toolchain fingerprint (`components/readme/bundle/seal.py`). A different interpreter patch version,
operating system or tool version reopens `EXTRACTING` for the candidate and every later stage then makes
live provider calls. The 35 bundle records under `candidates/` that carry an environment today all say
Python `3.13.2`, Windows. A hosted seal is therefore a re-seal of a natively sealed candidate; the self-hosted seal is the one that
can be a no-op (`docs/OPERATIONS_RUNBOOK.md` section 8).

## 2. Before anything is registered: this repository is public

Facts read from GitHub on 2026-10-12 (read-only): `babar-raza/repository-presenter` is **public** and
owned by a user account; no self-hosted runner is registered; fork-pull-request approval is
`first_time_contributors`; default workflow permissions are `read`.

GitHub's own guidance is not to use a self-hosted runner with a public repository, because a pull request
from a fork can propose a workflow that runs on it. The YAML guard of section 1 cannot help: a fork's pull
request carries its own copy of the workflows, so it can ask for the labels itself. What does help is
outside the YAML, and the preflight checks it (`runner:fork-approval`):

1. **Require approval for every outside contributor's run** (Settings > Actions > General > Fork pull
   request workflows > *Require approval for all external contributors*). The current setting lets a
   contributor who has had one commit accepted run workflows without approval. Do this **before** the
   runner is registered.
2. **Read before approving.** Never approve a fork run on a pull request that touches `.github/` or any
   `runs-on`, whatever else it does. The approval click is the whole control.
3. Keep write access to the owner alone. A collaborator with write access can push a branch whose
   workflow asks for the labels; branch protection does not stop a job that starts from a branch.
4. If the owner is ever willing to move the repository into an organization, an organization runner
   **group limited to selected workflows** (`present.yml@refs/heads/main`) closes this class of attack
   outright, because the runner then refuses any other workflow regardless of its YAML. A user-owned
   repository has no runner groups. This is a decision for the owner; it changes every URL, the App
   installation and the secrets, and is not assumed here.

If item 1 cannot be done, keep the default (hosted). The preflight reports it as NO-GO and the variable
stays unset.

## 3. Setup on this machine (owner steps, in order)

Machine facts read on 2026-10-12 (read-only): Windows 11 **Home** 10.0.26200 (no Hyper-V, no Windows
Sandbox, no `secpol.msc`); G: has 299 GiB free (D: 53 GiB, E: 27 GiB, so the runner lives on G:); the
presenter's interpreter of record is `D:\Python313\python.exe` 3.13.2 (the owner's `py` launcher lists only a
per-user 3.13.15, which is not the environment of record and which the service account could not read);
the toolchain registry is `D:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt` (its entries were written against
`C:\tools\...`; `core/toolchains.py` re-roots them under the registry's own folder). Two runners already
exist on this machine, **neither of which is used or touched here**:
`D:\tools\actions-runner-cells-foss` (registered to a product repository) and `D:\actions-runner`
(registered to `babar-raza/local-telemetry`). Neither runs as a service now.

Run the PowerShell below **elevated**. Nothing here is run by an agent.

### 3.1 The service account (least privilege)

```powershell
$bytes = New-Object byte[] 36
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$password = [Convert]::ToBase64String($bytes)        # 48 characters; keep it in the password manager
New-LocalUser -Name rp-seal -FullName 'Repository Presenter seal runner' `
  -Description 'Service account of the self-hosted seal runner; no interactive use' `
  -Password (ConvertTo-SecureString $password -AsPlainText -Force) `
  -PasswordNeverExpires -UserMayNotChangePassword
Add-LocalGroupMember -Group Users -Member rp-seal
Get-LocalGroupMember -Group Administrators           # rp-seal must not be listed
Get-LocalGroupMember -Group 'Remote Desktop Users'   # nor here
```

A standard user, in no administrative group. Windows 11 Home has no local-policy editor, so "deny logon"
rights are not set here; the controls are the random password and the account being used by nothing but
the service. `runas /user:rp-seal` (section 3.8) needs the password, which is why it is kept.

### 3.2 Folders and permissions

Windows gives `Authenticated Users` **Modify** on the roots of D: and G: and every folder that inherits it
(read with `icacls` on 2026-10-12). Any local account, `rp-seal` included, can therefore read and change
files under D: and G: that carry no restrictive ACL of their own. So the runner's own tree blocks
inheritance, and the places that must not be reachable are denied by name:

```powershell
New-Item -ItemType Directory G:\rp-runner\runner, G:\rp-runner\cache\pip | Out-Null
icacls G:\rp-runner /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' 'rp-seal:(OI)(CI)M'

# The other runners' credentials (an RSA key that impersonates a runner of another repository):
icacls D:\tools\actions-runner-cells-foss /deny 'rp-seal:(OI)(CI)F'
icacls D:\actions-runner                  /deny 'rp-seal:(OI)(CI)F'
# The owner's checkouts and OneDrive copy (may take a while to propagate):
icacls E:\Users\prora                     /deny 'rp-seal:(OI)(CI)F'

# The toolchains are read and executed, never changed by a job:
icacls D:\tools\rp-toolchains /deny 'rp-seal:(OI)(CI)(W,D,DC)'
```

Read the result with `icacls <path>`. `rp-seal` reads and executes `D:\Python313`, `C:\Program Files`
and `D:\tools\rp-toolchains` through the `Users` group already. Two limits to know: a tool that must write
inside its own home (rustup and npm keep a lock or a cache there) will say so in the first dry run; give
back `Modify` on that one subfolder, nothing wider, and record it. And the roots of D: and G: stay
world-modifiable for every other folder (residual risk R2, section 4); removing `Authenticated Users` from
those roots (`icacls G:\ /remove 'Authenticated Users'`) closes it but re-ACLs the whole volume and can
break other software, so it is an owner decision, not a step.

Optional, recommended: bound what a job can write to the volume, per account (NTFS quota; the first
`track` scans the volume):

```powershell
fsutil quota track G:
fsutil quota modify G: 53687091200 64424509440 "$env:COMPUTERNAME\rp-seal"   # warn at 50 GiB, stop at 60 GiB
fsutil quota enforce G:
```

### 3.3 No LAN egress for the account

Examples run upstream code with network access. Block that code from the owner's home network (the
router, other computers, printers), leave the Internet open:

```powershell
$sid = (New-Object Security.Principal.NTAccount('rp-seal')).Translate([Security.Principal.SecurityIdentifier]).Value
New-NetFirewallRule -DisplayName 'rp-seal: no LAN egress' -Direction Outbound -Action Block -Profile Any `
  -LocalUser "D:(A;;CC;;;$sid)" `
  -RemoteAddress '10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16','100.64.0.0/10','fc00::/7','fe80::/10'
```

DNS is answered by a Windows service, not by the account's processes, so it is not blocked. A block rule
beats any allow rule: if the LLM gateway resolves to a private address, narrow the ranges to leave that one
address out. Loopback is not blocked (build servers need it).

### 3.4 Download the runner, pinned, and verify it

Pinned: `actions/runner` **v2.338.0** (released 2026-10-06), `actions-runner-win-x64-2.338.0.zip`, SHA-256
`f48e0750a21812bca5f82de5f7f5aeae71abee647fab5a582f1742d07eba455f` (the release page's published checksum
and the asset's own digest agree, read 2026-10-12). If a newer release is current when you do this, take the
version and checksum from its release page; never extract an archive whose checksum you did not compare.

```powershell
Set-Location G:\rp-runner\runner
$version = '2.338.0'
$zip = "actions-runner-win-x64-$version.zip"
Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v$version/$zip" -OutFile $zip
$expected = 'f48e0750a21812bca5f82de5f7f5aeae71abee647fab5a582f1742d07eba455f'
if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'checksum mismatch: do not extract' }
Expand-Archive $zip -DestinationPath .
Remove-Item $zip
```

### 3.5 Register it: repository scope, one repository, as a service

Register at the **repository** (not an account-wide or organization) level, so it can only ever be asked
for by `babar-raza/repository-presenter`. Get a one-hour registration token from Settings > Actions >
Runners > *New self-hosted runner* (Windows, x64) and paste it at the prompt or after `--token`; it is
single-use and is not saved anywhere. Keep the work folder at the default `_work` inside the runner folder:
`present.yml`'s housekeeping and `check_runner.py --job` find the runner folder (`.env`, `.path`) and the work
folder from it. There is no runner group to choose: a user-owned repository's runners have none, so the labels
are the only selector.

```powershell
.\config.cmd --url https://github.com/babar-raza/repository-presenter --token <REGISTRATION-TOKEN> `
  --name rp-seal-1 --labels repository-presenter-seal --work _work `
  --runasservice --windowslogonaccount ".\rp-seal" --replace
```

Leave out `--windowslogonpassword`: the configuration asks for it at a hidden prompt, which keeps the
password out of the command line and the shell history. Do not pass `--no-default-labels` (the workflow asks
for `self-hosted`, `windows` and `x64` as well as `repository-presenter-seal`) and do not pass
`--disableupdate` (the runner updates itself between jobs; staying current is the security posture). Pick a
neutral `--name`: the runner and machine names are printed in the public job log of every run.

```powershell
Get-Service 'actions.runner.babar-raza-repository-presenter.*'     # Running, Automatic
sc.exe failure 'actions.runner.babar-raza-repository-presenter.rp-seal-1' reset= 86400 actions= restart/60000/restart/60000//0
powercfg /change standby-timeout-ac 0                                # a sleeping machine queues the seal for 24 hours
```

### 3.6 The runner's environment: `.env` and `.path`

Both files live in the runner folder and are read when the service starts. Restart it after editing
(`Restart-Service 'actions.runner.babar-raza-repository-presenter.rp-seal-1'`).

`G:\rp-runner\runner\.env`: names the pinned interpreter and the registry, and nothing secret.

```
RP_SEAL_PYTHON=D:\Python313\python.exe
RP_TOOLCHAIN_REGISTRY=D:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt
PIP_CACHE_DIR=G:\rp-runner\cache\pip
```

`G:\rp-runner\runner\.path`: one line. Git for Windows' `bash` must come **before** `System32`, where WSL's
launcher `bash.exe` lives (a `shell: bash` step would otherwise run WSL and fail); `nodejs` is for `npm`,
which no registry entry provides.

```
C:\Program Files\Git\bin;C:\Program Files\Git\cmd;C:\Program Files\Git\usr\bin;C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Program Files\nodejs
```

Everything else a verifier needs resolves through `core/toolchains.py`: the registry first for `tsc`,
`cargo`, `cmake`, `g++` and `ninja`, the Windows install roots for `javac`, `dotnet`, `node` and `go`. The
service account's `PATH` is not the owner's, so the one thing to watch is `npm`: the three bundles that
record a toolchain fingerprint say `npm: absent` (it was not on the sealing shell's `PATH`), so putting
`nodejs` on the runner's `.path` makes the TypeScript verifier able to build and changes that one fingerprint
entry. `check_runner.py` prints the difference (`fingerprint`); it is an owner decision, recorded in
`docs/DECISION_LOG.md`, whether those candidates re-extract once or `npm` stays unresolved (and TypeScript
examples stay `BLOCKED_TOOLCHAIN`).

### 3.7 The gateway key and the other secrets: nothing on the machine

`GPT_OSS_API_KEY`, `GPT_OSS_ENDPOINT`, `GH_APP_ID` and `GH_APP_PRIVATE_KEY` are repository Actions secrets
(already set). A self-hosted seal receives them as step environment variables, only in the steps that name
them (`present.yml`: the gateway preflight, the present step and the failure-staging step; the App key only
in the token mint). They are never in `.env`, never a machine or user variable, never written by the
runner: `check_runner.py` fails if the runner's `.env` holds a credential-shaped name and warns if the
process environment does. Rotation therefore needs nothing on the machine
(`docs/CREDENTIAL_ROTATION_RUNBOOK.md` section 2.1).

### 3.8 Check the machine, as the service account

`check_runner.py` is read-only (section 5 of this file lists exactly what it checks and prints). It needs
only the bare interpreter; run it from any checkout, as the account the service uses:

```powershell
git clone --depth 1 https://github.com/babar-raza/repository-presenter G:\rp-runner\checkout
runas /user:rp-seal "cmd /k D:\Python313\python.exe -I G:\rp-runner\checkout\tools\runner\check_runner.py --work-dir G:\rp-runner\runner\_work --runner-dir G:\rp-runner\runner"
```

(`-I` keeps a stray `PYTHONPATH` out; the checkout is read-only reference, delete it with the rest in
section 6.) Exit
`0` and no `FAIL` row is the condition for `--confirm runner:host-check`. The same check runs inside every
self-hosted job, with `--job`, before the first provider call.

### 3.9 Auto-update and disk

The runner updates itself between jobs. The workflow empties the workspace and its own temp folders at both
ends of every job and the runner clears its temp folder at the start of each; the pip cache under
`G:\rp-runner\cache\pip` is content-addressed and verified against the lock's hashes. Once a month remove
what accumulates: `pip cache purge` (as `rp-seal`), and `_diag` logs older than 30 days:
`Get-ChildItem G:\rp-runner\runner\_diag | Where-Object LastWriteTime -lt (Get-Date).AddDays(-30) | Remove-Item`.
`check_runner.py` fails below 40 GiB free.

## 4. Isolation: what runs on the machine, and the risk that remains

What a seal executes: `present` clones one upstream repository (a read-only App token, push disabled), then
runs that repository's own install, build and README example code through `core/execution.py::execute`.
That wrapper is a **process and credential boundary, not a sandbox** (`docs/THREAT_MODEL.md` area 4): the
child gets an allow-listed environment with every credential-shaped name removed, no shell, no stdin, a hard
timeout and a disposable workspace with every toolchain cache redirected into it; its output is redacted of
live secret values. It has no filesystem confinement, no network confinement and no resource ceiling beyond
the wall clock. On a hosted runner the surrounding VM is destroyed afterwards; here the surrounding machine
is the owner's. The controls that stand in for that, and what each does and does not stop:

| Control | Stops | Does not stop |
|---|---|---|
| Dedicated standard account `rp-seal`, no admin, nothing of the owner's in its profile | a job reading the owner's profile, browser sessions, `gh` login, SSH keys, per-user environment variables (the gateway key lives in the owner's User environment) | reading or changing what `Authenticated Users` can on D: and G: (R2) |
| Runner tree with inheritance blocked; deny rules on the other runners, the checkouts, the toolchains' write | a job reading another runner's credentials, editing a compiler for the next job | any folder not named |
| Firewall: no private-range egress for the account | a job probing or attacking the home network | any Internet destination, including exfiltration |
| Secrets only in the steps that need them; job-scoped read-only App token, job-scoped state token | persistence of a credential; a token that outlives the job | a child process reading its parent's environment (R3) |
| `select-runner`: default branch and trusted triggers only; one workflow can name the labels | an accidental or hosted-side use of the runner | a fork pull request that rewrites its own workflow (section 2) |
| Workspace and temp folders emptied at both ends; per-job venv; 120-minute timeout; disk quota | state surviving into the next seal; a hung job holding the machine; a full disk | a file Windows holds open (a warning, retried next job) |
| `check_runner.py --job` before the first provider call | seals on a machine that is no longer the environment of record | anything it does not check |

**Not adopted, and why.** A Docker job container: the runner supports `container:` jobs only on Linux, and a
Linux container is not the environment of record. Windows Sandbox or Hyper-V: not in Windows 11 Home. A WSL2
Linux runner: a different environment of record, so every seal becomes a re-seal (the hosted path already is
that). An ephemeral, just-in-time runner (one job, then removed): needs a credential on this machine able to
register runners, which is worse than the persistent runner credential it would replace. A separate machine
or a virtual machine on a Windows edition with Hyper-V is the one change that removes R2 to R5; it is the
right answer if the residual risk below is not acceptable.

**Residual risk, stated plainly.** Upstream repository code runs on the owner's machine as `rp-seal`.

- **R1 Public repository.** A fork pull request that an approver lets run can run code on the runner.
  Closed by the approval setting (section 2) and by reading before approving, not by the YAML.
- **R2 Reach.** Code running as `rp-seal` can read and change any file on D: and G: that does not carry its
  own restrictive ACL, and can reach the Internet.
- **R3 Secrets in memory.** The gateway key is in the environment of the `present` process, which is the
  parent of the example subprocesses; a same-user child on Windows can read its parent's environment. The
  child's *environment* is stripped, its *access to the parent* is not. Bounded by: the key's own scope and
  spend limit at the gateway, the read-only one-hour App token, the job-scoped state token, and rotation after
  any suspicion (`docs/CREDENTIAL_ROTATION_RUNBOOK.md`).
- **R4 The runner's own credential.** `.credentials` and `.credentials_rsaparams` are readable by the account
  that runs jobs. A stolen copy can impersonate the runner and receive later jobs of this repository. Remove
  and re-register the runner after any suspicion (section 6).
- **R5 Persistence.** `rp-seal`'s profile (`C:\Users\rp-seal`) persists between jobs and is not cleaned by
  the workflow. Delete and recreate the account (section 6) every quarter and after any suspicion.
- **R6 Disclosure.** The runner name and the machine name appear in public job logs; `check_runner.py` prints
  no path, user or host.
- **R7 Availability.** If the machine is off or asleep, a seal waits up to 24 hours for a runner and then
  fails; nothing falls back to hosted (the variable is the switch). Pause sealing
  (`REPOSITORY_PRESENTER_SEALING_PAUSED=1`) when the machine will be away.
- **R8 Drift of the environment of record.** A tool or interpreter update changes the fingerprint and reopens
  `EXTRACTING`. `check_runner.py` fails on a different interpreter patch version and warns on a different
  toolchain fingerprint.

The owner accepts R1 to R8 by setting the variable, and records that acceptance in `docs/DECISION_LOG.md`.
If a mandatory control (section 7, O1, O3 to O8) is not in place, do not set it.

## 5. What `tools/runner/check_runner.py` checks

`python tools/runner/check_runner.py [--job] [--json] [--work-dir DIR] [--runner-dir DIR] [--min-free-gib N]
[--expected-python X.Y.Z] [--endpoint URL] [--no-network] [--root DIR]`. Read-only: it writes, installs and
registers nothing; it prints names, versions and verdicts, never a secret, an environment dump or a path of
the host; it sends no credential anywhere (a test pins the absence of any write-shaped call).

| Row | FAIL when |
|---|---|
| `os`, `python`, `python:pinned` | not Windows; the interpreter (and `RP_SEAL_PYTHON`) is not the patch version `present.yml` pins (`EXPECTED_PYTHON`, 3.13.2) |
| `bash`, `cygpath` | `bash` is the WSL launcher or absent, is not GNU bash, or cannot find `cygpath` |
| `git` | absent |
| `registry` | `RP_TOOLCHAIN_REGISTRY` names nothing that resolves |
| `tool:<name>` | a tool a verifier invokes does not resolve (`mvn` only warns: no verifier invokes Maven) |
| `fingerprint` | never; WARN lists tools that differ from the sealed bundles that record a fingerprint |
| `disk` | under 40 GiB free, not writable, or under OneDrive |
| `runner-env`, `runner-env:secrets`, `runner-path` | `.env` lacks `RP_SEAL_PYTHON` or `RP_TOOLCHAIN_REGISTRY`, holds a credential-shaped name, or `.path` has System32 before Git for Windows |
| `account` | never; WARN if an administrator |
| `environment` | never; WARN names credential-shaped variables set in the process |
| `gateway` | the endpoint does not answer (TCP, TLS and an HTTP status under 500, no key sent); skipped without `GPT_OSS_ENDPOINT` or with `--job` |

## 6. Switch on, switch off, roll back, remove

**Switch on** (after `hosting_preflight.py` says GO for H0, section 9.1 of the runbook):
`gh variable set REPOSITORY_PRESENTER_SEAL_RUNNER --body self-hosted-windows -R babar-raza/repository-presenter`.
The next `present.yml` run (a dispatch, or the daily `sealing-scheduled.yml` at 05:37 UTC) goes to the runner.
Run the H0 pilot first by dispatching `present.yml` for one Python repository and reading the job: the
`select-runner` log says `seal runner: self-hosted-windows (trusted trigger: workflow_dispatch)`, the verify
step has no `FAIL`, and afterwards `G:\rp-runner\runner\_work\repository-presenter\repository-presenter` is empty.

**Switch off:** `gh variable delete REPOSITORY_PRESENTER_SEAL_RUNNER -R babar-raza/repository-presenter`. The
next run is hosted; nothing else changes. A hosted seal of a natively sealed candidate is a re-seal.
Stopping sealing altogether is the pause variable (`docs/OPERATIONS_RUNBOOK.md` section 4).

**Remove the runner** (after a suspicion, or for good): stop and unregister, then delete.

```powershell
Set-Location G:\rp-runner\runner
.\config.cmd remove --token <REMOVAL-TOKEN>        # Settings > Actions > Runners > the runner > Remove
# or, if the service is already gone: Settings > Actions > Runners > Remove, then:
Get-Service 'actions.runner.babar-raza-repository-presenter.*'
Remove-NetFirewallRule -DisplayName 'rp-seal: no LAN egress'
Remove-LocalUser rp-seal
Remove-Item -Recurse -Force C:\Users\rp-seal -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force G:\rp-runner
```

Re-registering after a removal is a new registration token and section 3.5 again; rotating the account (R5)
is the same sequence from `Remove-LocalUser` and section 3.1. After a suspected compromise also rotate
`GPT_OSS_API_KEY` and `GH_APP_PRIVATE_KEY` (`docs/CREDENTIAL_ROTATION_RUNBOOK.md`).

## 7. Owner actions, in order

| # | Action | Where | Verified by |
|---|---|---|---|
| O1 | Set fork-run approval to *all external contributors* | Settings > Actions > General | `runner:fork-approval` |
| O2 | Decide to accept R1 to R8, or to use a separate machine, or to stay hosted; record it | `docs/DECISION_LOG.md` | the decision |
| O3 | Create the account `rp-seal` | 3.1 | `Get-LocalGroupMember` |
| O4 | Create `G:\rp-runner`, block inheritance, add the deny rules (and the optional quota) | 3.2 | `icacls` |
| O5 | Add the firewall rule | 3.3 | `Get-NetFirewallRule` |
| O6 | Download the pinned runner and compare its checksum | 3.4 | the `throw` |
| O7 | Register it at repository scope as a service under `rp-seal`; keep sleep off | 3.5 | `runner:registered` |
| O8 | Write `.env` and `.path`; restart the service | 3.6 | `check_runner.py` |
| O9 | Run `check_runner.py` as `rp-seal`; confirm | 3.8 | `--confirm runner:host-check` |
| O10 | Confirm the isolation items (O3 to O5) | 4 | `--confirm runner:isolation` |
| O11 | Decide the `npm` fingerprint question | 3.6 | `docs/DECISION_LOG.md` |
| O12 | Run `hosting_preflight.py --stage H0`; set the variable; dispatch the H0 pilot | 6 | the job log |

## 8. What was checked here, and what was not

Checked in this repository without a runner, a network write or a provider call: the workflow's structure
and every rule of section 1 (`tests/test_present_runner_selection.py`, each rule with a negative control);
the `select-runner` script executed under bash against every trigger, ref and hostile variable value, and the
workspace guard executed against a throwaway runner layout; `actionlint` 1.7.12 clean; the generated
inventory in the runbook; the preflight's runner items against a fake `gh`
(`tests/test_hosting_preflight.py`); `check_runner.py` against injected resolvers, probes and fetches
(`tests/test_check_runner.py`) and, once, read-only on this machine as the owner's account. `act -n` cannot
plan the `present` job (its `runs-on` comes from another job's output, known only when that job has run);
`act` (v0.2.89, image `catthehacker/ubuntu:act-24.04`) did run the `select-runner` job itself, with GitHub's
own expression evaluation, for four cases: variable unset (hosted outputs), `self-hosted-windows` from a
feature branch (refused), an unrecognised value (refused) and `self-hosted-windows` from the default branch
(the four labels).

Not proven, said plainly: any step on the Windows runner (the venv, the cygpath and `find` housekeeping under
the real service account, `actions/checkout` and the artifact actions on Windows); that every tool resolves for
`rp-seal`'s `PATH` and permissions; that the sealed bundles stay a no-op under it; GitHub's fork-approval
behaviour; the firewall rule's effect on this machine's network; the quota. Each is what the H0 pilot is for.
