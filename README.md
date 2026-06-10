# Vending Auto Setup

A CLI tool for preparing Ubuntu 22.04 LTS Desktop machines used in vending kiosks. It installs required software, configures the display and touchscreen, sets up remote access, and provides a local web dashboard — all with minimal commands.

## Features

### Core Tools Installation
- **Node.js** (v22 LTS) from NodeSource apt repository
- **Docker Engine** from official Docker apt repository
- **Git** from Ubuntu apt
- **AnyDesk** from AnyDesk DEB repository
- **WireGuard** VPN

### Display & Touchscreen Configuration
- Detect X11 / Wayland session type
- List connected monitor outputs (via `xrandr`)
- List touchscreen devices with xinput ID (via `udevadm` kernel database)
- Apply display rotation at runtime (`xrandr`)
- Map touchscreen coordinates to match rotation (`xinput`)
- Persist rotation across reboots via `~/.xprofile` + retry script
- Persist touchscreen matrix via Xorg `InputClass` config

### WireGuard VPN
- Install WireGuard package
- Create config templates
- Validate configs without printing secret keys
- Save configs to app storage without applying
- Sync configs to `/etc/wireguard/` and manage `systemctl` service
- Full config history with secret masking by default
- Unsync (disable and remove active config)

### Web Dashboard
- Local Flask HTTP dashboard at `http://0.0.0.0:8888`
- **Display page** — real-time status bar showing session type, connected monitors, detected touchscreens, and all config file statuses with inline file viewer
- **Dashboard** — system status for all tools, VPN, remote access, and web server
- **Commands** — copy-paste command references for install, reset, and WireGuard workflows
- Runs as a background systemd service

### Remote Access
- AnyDesk installation and service management
- Status check: version, device ID, online status, and service state

### Self-Update
- `vas update` downloads the latest source from GitHub and replaces `/opt/vending-auto-setup` in place

---

## Requirements

- Ubuntu 22.04 LTS Desktop (x86_64)
- Internet access (for initial installation)
- X11 session (for display/touchscreen commands)

---

## First-Time Installation on a New Machine

The machine does not need Git pre-installed. Use `wget` to run the bootstrap script:

### One-line install (installs CLI + all components)

```bash
wget -qO- https://raw.githubusercontent.com/phanuphun/vending-auto-setup/main/scripts/install.sh | sudo bash -s -- --install-cli install --component all
```

This installs:
- Node.js, Docker, Git, AnyDesk, WireGuard
- CLI wrapper at `/usr/local/bin/vas` and `/usr/local/bin/vending-auto-setup`
- Source at `/opt/vending-auto-setup`

### Install CLI only (no packages yet)

```bash
wget -qO- https://raw.githubusercontent.com/phanuphun/vending-auto-setup/main/scripts/install.sh | sudo bash -s -- --install-cli check
```

### Download source manually (no Git required)

```bash
sudo apt update && sudo apt install -y wget tar python3

wget -O vending-auto-setup.tar.gz https://github.com/phanuphun/vending-auto-setup/archive/refs/heads/main.tar.gz
tar -xzf vending-auto-setup.tar.gz
mv vending-auto-setup-main vending-auto-setup
cd vending-auto-setup

sudo PYTHONPATH=src python3 -m cli install --component all
```

---

## Usage

After installation, use `vas` or `vending-auto-setup` as the command.

### Check system status

```bash
vas check
```

Shows session type, display config, touchscreen config, all installed tools, remote access, VPN, and web server status.

### Install components

```bash
sudo vas install --component all
sudo vas install --component node --component docker
sudo vas install --component wireguard
```

Supported components: `node`, `docker`, `git`, `wireguard`, `anydesk`, `all`

### Update CLI

```bash
sudo vas update
```

---

## Display & Touchscreen

### Check xrandr and xinput

```bash
vas display status --display :0
```

### List touchscreen devices with xinput ID

```bash
vas display list-touch
vas display list-touch --display :0
```

Output:
```
  ID  Name
------------------------------------------------
  13  Vending Virtual Touchscreen
```

### Apply rotation and touchscreen mapping (runtime, immediate)

```bash
vas display apply --display :0 --output Virtual1 --touch "Vending Virtual Touchscreen" --rotate left
```

Supported rotations: `normal`, `left`, `right`, `inverted`

### Persist display rotation at login

```bash
vas display persist-session --display :0 --output Virtual1 --touch "Vending Virtual Touchscreen" --rotate left
```

> **Do not use `sudo`** — this writes to the current user's `~/.xprofile` and `~/.config/vending-auto-setup/display-session.sh`

### Persist touchscreen matrix via Xorg

```bash
sudo vas display persist-xorg --touch "Vending Virtual Touchscreen" --rotate left
```

Writes `/etc/X11/xorg.conf.d/99-vending-touchscreen.conf`

### Reset display config

```bash
sudo vas reset --component display
```

---

## Web Dashboard

### Start as a background service

```bash
sudo vas server start --host 0.0.0.0 --port 8888
```

Then open `http://<machine-ip>:8888` in a browser.

### Service management

```bash
vas server status
sudo vas server stop
```

### Run in foreground (for debugging)

```bash
vas server run --host 0.0.0.0 --port 8888
```

---

## WireGuard

```bash
# Install WireGuard
sudo vas wireguard install

# Create config template
vas wireguard init-config --name wg0 --output ./wg0.conf
# Edit wg0.conf with your keys and peers

# Validate config
vas wireguard validate --config ./wg0.conf

# Save to app storage (does not apply yet)
vas wireguard save --name wg0 --config ./wg0.conf

# Apply to /etc/wireguard and enable service
sudo vas wireguard sync --name wg0

# Check status
vas wireguard status --name wg0

# View config history (secrets masked by default)
vas wireguard history --name wg0
vas wireguard show --name wg0 --id <history-id>
vas wireguard show --name wg0 --id <history-id> --reveal-secrets

# Disable and remove active config
sudo vas wireguard unsync --name wg0
```

> **Never commit private keys or preshared keys to the repository.**

---

## Uninstall & Reset

```bash
# Uninstall packages only (keeps configs)
sudo vas uninstall --component docker
sudo vas uninstall --component all

# Reset: uninstall + remove managed configs
sudo vas reset --component node
sudo vas reset --component display
sudo vas reset --component all
```

Supported components for reset: `node`, `docker`, `git`, `wireguard`, `anydesk`, `display`, `all`

> Docker reset does **not** remove `/var/lib/docker` (volumes and images are preserved).

---

## Dry Run

Any command supports `--dry-run` to preview what would be executed without making changes:

```bash
sudo vas install --component all --dry-run
sudo vas display persist-xorg --touch "Vending Virtual Touchscreen" --rotate left --dry-run
```

---

## Virtual Touchscreen (VirtualBox development)

For testing without a physical touchscreen, create a virtual device using `uinput`:

```bash
sudo apt install -y python3-evdev
sudo python3 scripts/dev/virtual_touchscreen.py --width 1920 --height 1080
```

Then in another terminal:

```bash
xinput list                  # confirm "Vending Virtual Touchscreen" appears
vas display list-touch       # shows device with xinput ID
xinput test-xi2 13           # monitor raw touch events in real-time
```

---

## Local Development

### Prerequisites

- Python 3.10+ (`python3 --version`)
- Git
- `uv` (recommended) or `pip`

Install `uv` if not present:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Moving the project to a new machine

If you already have the source (USB, zip, scp) and don't want to re-clone:

```bash
# Copy the project folder to the new machine, then:
cd vending-auto-setup

# Remove the old virtual environment (not portable between machines)
rm -rf .venv

# Recreate it fresh
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

> `.venv` is machine-specific — always delete and recreate it when copying the project to a new machine.

---

### Clone and set up (new machine)

```bash
git clone https://github.com/phanuphun/vending-auto-setup.git
cd vending-auto-setup
```

**Using uv (recommended):**

```bash
uv venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

uv pip install -e ".[dev]"
```

**Using pip (fallback):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run without installing system-wide

```bash
vas check
PYTHONPATH=src python3 -m cli check
```

### Run tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
```

### Type checking and linting

```bash
# Type check
mypy src tests

# Lint / auto-fix
ruff check src tests
ruff format src tests
```

### Verify the web dashboard locally

```bash
PYTHONPATH=src python3 -m server --host 127.0.0.1 --port 8888
# Open http://127.0.0.1:8888
```

---

## Project Structure

```
src/
  cli.py            — CLI entry point and argument parser
  config.py         — Default configuration values
  installers.py     — Phase 1 package installer (Node, Docker, Git, AnyDesk)
  display.py        — Display/touchscreen configuration (xrandr, xinput, udevadm)
  status.py         — System status collectors (check command)
  wireguard.py      — WireGuard config management
  server.py         — Flask web dashboard
  server_service.py — systemd service setup
  reset.py          — Uninstall and reset logic
  updater.py        — Self-update from GitHub
  runner.py         — Command execution with dry-run support
  clock.py          — System clock preflight check
  web/
    templates/      — Jinja2 HTML templates
    static/         — CSS and static assets
scripts/
  install.sh        — Bootstrap installer (no Git required)
  dev/
    virtual_touchscreen.py — Virtual touchscreen for VirtualBox testing
tests/              — pytest test suite
```

---

## Troubleshooting

**Terminal won't open in VirtualBox**
```text
Cause: locale not set to UTF-8
Fix: set LANG=en_US.UTF-8 in /etc/default/locale, then sudo locale-gen --purge && sudo reboot
```

**`xinput` shows no touchscreen**
```bash
# Check if virtual touchscreen script is running
sudo python3 scripts/dev/virtual_touchscreen.py --width 1920 --height 1080
xinput list
```

**`xrandr` shows no connected output**
```bash
xrandr --query   # use the name shown as "connected"
```

**Docker requires `sudo`**
```bash
sudo usermod -aG docker $USER
sudo reboot
```

**`vas check` shows wrong paths under `sudo`**

This is expected. Running `sudo vas check` uses `SUDO_USER` to resolve the correct home directory automatically. The display config paths will always point to the logged-in user's home, not `/root`.

**Display script is "not executable"**

The server writes the script with `755` permissions and transfers ownership to the real user automatically. If this shows as a warning, run `persist-session` again without `sudo`.
