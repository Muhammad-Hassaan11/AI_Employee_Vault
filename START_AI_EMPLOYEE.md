# START HERE — Running Your AI Employee (Operator Guide)

This is the hands-on guide: exactly which commands to run, in what
order, on **your PC (Local agent)** and on the **Oracle Cloud VM (Cloud
agent)**. Architecture details live in [README.md](README.md).

---

## Part 1 — Start the LOCAL agent (your Windows PC)

The Local agent owns approvals, WhatsApp, payments, and every final
send/post. All commands below run from the vault root
(`Desktop\AI_Employee_Vault`) in PowerShell.

### 1.1 One-time setup

```powershell
# a) Create your credentials file (gitignored — never synced)
Copy-Item .env.example .env
notepad .env
# Fill in: AGENT_ROLE=local, GMAIL_*, SMTP_*, TWILIO_*, LINKEDIN_*,
#          ODOO_*, META_*, X_*  (leave blank what you don't use yet)

# b) Verify Claude Code works
claude --version

# c) (Optional) Local Odoo for testing instead of the cloud one
cd Odoo; docker compose up -d; cd ..
# open http://localhost:8069 → create DB "business" → install Invoicing
```

### 1.2 Start it

```powershell
# EITHER: schedule everything (recommended — runs even when you forget)
powershell -File Scripts\register_tasks.ps1
# registers: Gmail watcher (15 min), WhatsApp (15 min), LinkedIn (60 min),
#            approval executor (10 min), reasoning loop (30 min), weekly audit

# OR: run one full cycle by hand to watch it work
powershell -File Scripts\run_employee.ps1
```

### 1.3 Daily driving

| You want to… | Do this |
|---|---|
| Give Atlas work | Drop a file into `Inbox/` or `Needs_Action/` |
| Approve an action | Open the file in `Pending_Approval/` in Obsidian, change `status: pending` → `approved` |
| See what happened | Open `Dashboard.md`, `Logs/[today].md`, `Logs/audit.jsonl` |
| Force a long task to completion | `powershell -File Scripts\ralph_loop.ps1 "<task>"` (Ralph Wiggum loop) |
| Run the CEO briefing now | `powershell -File Scripts\weekly_audit.ps1` |

---

## Part 2 — Create the Oracle Cloud VM (Cloud agent)

The Cloud agent runs 24/7: email triage, draft replies, social drafts —
**draft-only**, everything still comes to you for approval.

### 2.1 Provision the VM (Oracle Cloud console, ~10 min)

1. Sign in at <https://cloud.oracle.com> (Free Tier is enough).
2. **Compute → Instances → Create Instance**
   - Image: **Ubuntu 24.04** (or 22.04)
   - Shape: `VM.Standard.A1.Flex` (Ampere, 2 OCPU / 12 GB — free tier)
     or `VM.Standard.E2.1.Micro`
   - Add your **SSH public key** (or download the generated private key)
3. Open web ports for Odoo HTTPS: **Networking → Virtual Cloud Networks
   → your VCN → Security Lists → Default → Add Ingress Rules**:
   - Source `0.0.0.0/0`, TCP port `80`
   - Source `0.0.0.0/0`, TCP port `443`
4. Note the instance's **public IP**.
5. (For Odoo HTTPS) At your DNS provider, add an **A record**, e.g.
   `odoo.yourdomain.com → <public IP>`.

### 2.2 Connect to the VM

From your PC:

```powershell
ssh -i C:\path\to\your_private_key ubuntu@<PUBLIC_IP>
```

---

## Part 3 — Pull this vault into the Oracle VM

The two agents share the vault through **GitHub**. Your repo is
`https://github.com/Muhammad-Hassaan11/AI_Employee_Vault` (adjust if
yours differs).

### 3.1 First push everything from your PC

```powershell
# on your PC, in the vault root
git add -A
git commit -m "Platinum tier: cloud agent + synced vault"
git push origin main
```

### 3.2 Give the VM access to the repo (pick ONE)

**Option A — Fine-grained Personal Access Token (easiest).** On GitHub:
Settings → Developer settings → Fine-grained tokens → Generate; scope it
to just this repo with **Contents: Read and write**. Then on the VM:

```bash
git clone https://<TOKEN>@github.com/Muhammad-Hassaan11/AI_Employee_Vault.git ~/AI_Employee_Vault
# store the token so pulls/pushes don't ask again:
cd ~/AI_Employee_Vault && git config credential.helper store
```

**Option B — SSH deploy key (cleaner long-term).** On the VM:

```bash
ssh-keygen -t ed25519 -C "ai-employee-cloud" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
# copy the output → GitHub repo → Settings → Deploy keys → Add key
# → tick "Allow write access"
git clone git@github.com:Muhammad-Hassaan11/AI_Employee_Vault.git ~/AI_Employee_Vault
```

### 3.3 Bootstrap the cloud agent (one command)

```bash
cd ~/AI_Employee_Vault
bash Cloud/setup_oracle_vm.sh
```

This installs git/Python/Node 24/Claude Code/Docker, opens the firewall,
installs the systemd units (`ai-watchdog.service` keeps the watchers
alive; `ai-employee.timer` runs a reasoning cycle every 30 min), and
starts Odoo if `ODOO_DOMAIN` is set.

### 3.4 Configure the cloud (cloud-zone secrets ONLY)

```bash
nano ~/AI_Employee_Vault/.env
```

Set: `AGENT_ROLE=cloud`, `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` (read),
`LINKEDIN_*`, `ODOO_URL=https://odoo.yourdomain.com`, `ODOO_DB`,
`ODOO_USER`, `ODOO_PASSWORD`, `ODOO_DOMAIN`, `ODOO_DB_PASSWORD`.

**Leave EMPTY on the VM:** `SMTP_*` (sending), `TWILIO_*` (WhatsApp),
and anything payment/banking. That's the Platinum security rule — the
cloud can only ever draft.

```bash
claude login          # authenticate Claude Code once (browser link)
```

### 3.5 Start Odoo on the cloud (accounting, 24/7)

```bash
cd ~/AI_Employee_Vault
export $(grep -E '^ODOO_(DOMAIN|DB_PASSWORD)=' .env | xargs)
sudo -E docker compose -f Odoo/docker-compose.cloud.yml up -d
# first time: open https://odoo.yourdomain.com → create DB "business"
# → install the Invoicing app. Backups appear nightly in Odoo/backups/.
```

### 3.6 Verify the cloud agent

```bash
bash Scripts/run_employee_cloud.sh        # one full cycle by hand
systemctl status ai-watchdog.service      # watchers alive?
systemctl list-timers ai-employee.timer   # next scheduled run
journalctl -u ai-employee.service -f      # follow scheduled cycles
cat Updates/HEALTH_cloud.md               # health snapshot
```

---

## Part 4 — Prove it works (the Platinum demo)

1. **Shut your PC down.** Send yourself an email at the monitored Gmail.
2. Within ~30 min the VM: files a task → claims it
   (`In_Progress/cloud/`) → Claude drafts a reply into
   `Pending_Approval/EMAIL_*.md` (`status: pending`, `drafted_by: cloud`)
   → pushes to GitHub. Check from anywhere:
   `git log --oneline` on GitHub shows `sync(cloud): …`.
3. **Turn your PC on**, run `powershell -File Scripts\run_employee.ps1`
   (or let the scheduled task fire). It pulls the draft.
4. In Obsidian, open the draft, set `status: approved`.
5. Next local cycle: `approval_executor.py` **sends the email**, logs to
   `Logs/audit.jsonl`, moves everything to `/Done`, and the Dashboard
   shows the cloud's activity (merged from `/Updates/`).

---

## Part 5 — Command reference

### Local (PowerShell, from vault root)

| Command | What it does |
|---|---|
| `powershell -File Scripts\run_employee.ps1` | One full local cycle (sync → watchers → claim → Claude → approvals → merge → sync) |
| `powershell -File Scripts\register_tasks.ps1` | Register all Task Scheduler jobs (`-Unregister` removes) |
| `powershell -File Scripts\vault_sync.ps1` | Manual vault sync (pull + push) |
| `python Scripts\merge_updates.py` | Merge cloud updates into Dashboard now |
| `python Scripts\claim_task.py list` | Who has claimed what |
| `python Scripts\approval_executor.py` | Execute approved / archive rejected items now |
| `powershell -File Scripts\ralph_loop.ps1 "<task>"` | Persistence loop until task completes |

### Cloud (bash, from `~/AI_Employee_Vault`)

| Command | What it does |
|---|---|
| `bash Scripts/run_employee_cloud.sh` | One full cloud cycle (draft-only) |
| `bash Scripts/vault_sync.sh` | Manual vault sync |
| `python3 Scripts/health_monitor.py` | Health snapshot → `Updates/HEALTH_cloud.md` |
| `sudo systemctl restart ai-watchdog` | Restart the watcher supervisor |
| `journalctl -u ai-employee -n 100` | Last 100 log lines of scheduled cycles |
| `sudo docker compose -f Odoo/docker-compose.cloud.yml ps` | Odoo stack status |
| `ls Odoo/backups/` | Nightly database backups (7 kept) |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `claude: command not found` on VM | `sudo npm install -g @anthropic-ai/claude-code`, then `claude login` |
| Cloud pushes rejected | Both agents edited the same file; on the failing side run `git pull --rebase --autostash` then `git push`. The sync scripts already retry once. |
| Odoo not reachable via HTTPS | DNS A record must point at the VM **and** ports 80/443 must be open in BOTH the OCI Security List and the VM iptables (`setup_oracle_vm.sh` handles iptables). Give Caddy ~1 min to fetch the certificate. |
| Watcher dead on VM | `systemctl status ai-watchdog`; details in `Logs/audit.jsonl` (`process_exited` entries) |
| Nothing gets sent, ever | Correct — sends only happen on Local after you flip `status: approved`. Check `Pending_Approval/`. |
| Cloud claimed a WhatsApp task | It can't (work-zone filter), but if a task is mis-tagged the cloud-triage skill moves it back to `/Needs_Action` with a note. |

<!-- graph-links -->
## Related

- [[README]] · [[CLAUDE]] · [[Dashboard]] · [[Company_Handbook]]
