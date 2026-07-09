#!/usr/bin/env bash
# =============================================================================
# One-shot bootstrap for the ALWAYS-ON CLOUD AGENT on an Oracle Cloud VM
# (Ubuntu 22.04/24.04, x86 or Ampere ARM - both free-tier shapes work).
#
# What it does:
#   1. Installs git, Python 3, Node.js 24, Claude Code CLI, Docker
#   2. Clones (or updates) the vault repository
#   3. Creates .env from .env.example (you fill in cloud-safe values only!)
#   4. Opens the VM firewall for HTTP/HTTPS (Odoo behind Caddy)
#   5. Installs + enables the systemd units (watchdog, reasoning timer)
#   6. Starts the Odoo cloud stack (docker-compose.cloud.yml)
#
# Usage (on the VM, as the default 'ubuntu' user):
#   export VAULT_REPO="https://github.com/<you>/AI_Employee_Vault.git"
#   curl -fsSL https://raw.githubusercontent.com/<you>/AI_Employee_Vault/main/Cloud/setup_oracle_vm.sh | bash
#   # or, if you already cloned:  bash Cloud/setup_oracle_vm.sh
#
# SECURITY: the cloud .env must contain ONLY cloud-zone credentials
# (Gmail read + LinkedIn draft + Odoo). NEVER put WhatsApp sessions,
# banking, SMTP send or payment tokens on the VM - those stay LOCAL.
# =============================================================================
set -euo pipefail

VAULT_REPO="${VAULT_REPO:-}"
VAULT_DIR="${VAULT_DIR:-$HOME/AI_Employee_Vault}"
VM_USER="$(whoami)"

step() { echo -e "\n=== $1 ==="; }

# --- 1. Base packages --------------------------------------------------------
step "Installing base packages (git, python3, curl)"
sudo apt-get update -y
sudo apt-get install -y git python3 python3-pip curl ca-certificates

step "Installing Node.js 24 (for Claude Code CLI)"
if ! command -v node >/dev/null || [[ "$(node -v | cut -c2-3)" -lt 24 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

step "Installing Claude Code CLI"
if ! command -v claude >/dev/null; then
    sudo npm install -g @anthropic-ai/claude-code
fi
echo "claude version: $(claude --version || echo 'run: claude login (or set ANTHROPIC_API_KEY)')"

step "Installing Docker (for the Odoo stack)"
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$VM_USER"
fi

# --- 2. Clone or update the vault -------------------------------------------
step "Fetching the vault repository"
if [[ -d "$VAULT_DIR/.git" ]]; then
    git -C "$VAULT_DIR" pull --rebase --autostash
elif [[ -n "$VAULT_REPO" ]]; then
    git clone "$VAULT_REPO" "$VAULT_DIR"
else
    echo "ERROR: vault not found at $VAULT_DIR and VAULT_REPO is not set."
    echo "  export VAULT_REPO=\"https://github.com/<you>/AI_Employee_Vault.git\" and re-run."
    exit 1
fi
cd "$VAULT_DIR"
git config user.name  "AI Employee Cloud"
git config user.email "cloud-agent@ai-employee.local"

# --- 3. Cloud .env (cloud-zone secrets ONLY) ---------------------------------
step "Preparing .env"
if [[ ! -f .env ]]; then
    cp .env.example .env
    sed -i 's/^AGENT_ROLE=.*/AGENT_ROLE=cloud/' .env || echo "AGENT_ROLE=cloud" >> .env
    echo ">>> EDIT $VAULT_DIR/.env now: fill in GMAIL_* (read), LINKEDIN_*, ODOO_*."
    echo ">>> LEAVE EMPTY: SMTP_*, TWILIO_* (WhatsApp), payment/banking values - those are LOCAL-only."
fi

# --- 4. Firewall: allow HTTP/HTTPS for Odoo behind Caddy ---------------------
step "Opening firewall ports 80/443 (Oracle VMs use iptables + netfilter-persistent)"
sudo iptables -C INPUT -p tcp --dport 80  -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 80  -j ACCEPT
sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true
echo "(Also add Ingress Rules for 80/443 in the OCI Console: VCN -> Security List)"

# --- 5. systemd units --------------------------------------------------------
step "Installing systemd units (watchdog + reasoning timer)"
for unit in ai-watchdog.service ai-employee.service ai-employee.timer; do
    sed -e "s|__VAULT_DIR__|$VAULT_DIR|g" -e "s|__VM_USER__|$VM_USER|g" \
        "Cloud/systemd/$unit" | sudo tee "/etc/systemd/system/$unit" > /dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --now ai-watchdog.service
sudo systemctl enable --now ai-employee.timer
echo "watchdog:  $(systemctl is-active ai-watchdog.service)"
echo "timer:     $(systemctl is-active ai-employee.timer)"

# --- 6. Odoo cloud stack ------------------------------------------------------
step "Starting Odoo (Postgres + Odoo 19 + Caddy HTTPS + nightly backups)"
if [[ -n "${ODOO_DOMAIN:-}" ]]; then
    sudo docker compose -f Odoo/docker-compose.cloud.yml up -d
    echo "Odoo starting at https://$ODOO_DOMAIN (Caddy fetches the certificate automatically)"
else
    echo "SKIPPED: set ODOO_DOMAIN in .env (a DNS name pointing at this VM) and run:"
    echo "  sudo docker compose -f Odoo/docker-compose.cloud.yml up -d"
fi

step "Done"
cat <<'EOF'
Next steps:
  1. nano ~/AI_Employee_Vault/.env      (cloud-zone credentials only!)
  2. claude login                        (authenticate Claude Code once)
  3. bash Scripts/run_employee_cloud.sh  (run one cycle manually to verify)
  4. journalctl -u ai-employee -f        (watch scheduled runs)
See START_AI_EMPLOYEE.md for the full operator guide.
EOF
