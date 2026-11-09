# Permission and safety model

Instead of trusting the agent, we define in layers what the agent **cannot do**. Each layer catches what the previous one missed.

| Layer | Where | What it does | Limitation |
|---|---|---|---|
| 1. Claude Code permissions | `.claude/settings.json` | allow / ask / deny lists | Cannot catch indirect Bash commands |
| 2. Guard hook | `.claude/hooks/guard.py` (PreToolUse) | Blocks writes to the original project, the workspace copy, evidence files and the harness itself; blocks reading answer keys | Heuristic; an indirect Bash write can slip through |
| 3. Harness rules | `src/pmi` + `config/policy.yaml` | Statuses change only via `pmi verify`. Pre-registration is mandatory. Profile confirmation is required. Budget, timeout and replicate limits apply. | — |
| 4. Integrity (backstop) | `pmi integrity` | The original project and the workspace copy are compared against the sha256 snapshot. The ledger hash chain and artifact hashes are checked. | Does not prevent writes, **detects** them |
| 5. Human gates | `ask` rules | init, profile set, adapter validate/confirm, budget extend, arbitrary `python`, `git` | — |

## Where the agent can write
- `runs/<id>/workspace/pmi_adapter.py` (the only executable file)
- `runs/<id>/workspace/scratch/**`
- `runs/<id>/notes/**`

## Where it can never write
- The original investigated project (path read from `runs/*/manifest.json`)
- `runs/<id>/workspace/target/**` (the baseline copy)
- `ledger.sqlite`, `manifest.json`, `snapshot.json`, `profile.json`, `adapter.json`, `budget.json`, `report.md`, `artifacts/**`, `scan/**`
- Harness: `src/`, `config/`, `.claude/`, `claude_config/`, `setup_claude_config.py`, `tests/`, `domain_packs/`, `CLAUDE.md`, `pyproject.toml`. This rule is lifted with `PMI_DEV_MODE=1`.

## Human gates
| Command | Why |
|---|---|
| `pmi init` | Which project gets audited is a human decision |
| `pmi use` | Switching the active run |
| `pmi profile set` | Facts about the project become final through human confirmation, not agent guesses |
| `pmi adapter validate` | Project code runs for the first time |
| `pmi adapter confirm` | That the adapter mirrors the project is accepted on human declaration only when no reported metric exists |
| `pmi budget extend` | Cost and time limits |
| `python ...`, `git ...` | Arbitrary code execution and repository changes |

## Running project code
Project code runs only inside the `python -m pmi.engine.worker` subprocess, with `cwd = workspace`:
- **Network:** with `execution.network: blocked`, the socket layer is patched (connect, create_connection, getaddrinfo). This is **not an OS sandbox**: native extensions or subprocesses spawned by project code can bypass it. For untrusted projects, run the worker inside a network-less container/VM as well.
- **Time:** `timeout_seconds_per_experiment`
- **Environment:** HTTP(S)_PROXY variables are cleared.

## Developing the harness
To develop the harness, start the session like this:
```bash
PMI_DEV_MODE=1 claude          # Git Bash / Linux / macOS
$env:PMI_DEV_MODE=1; claude     # PowerShell
```
Even in this mode, original projects and evidence files stay protected.
