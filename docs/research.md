# Research Notes

## Bootstrap Flow

Ubuntu 22.04 Desktop typically ships with Python 3.10 but may not have Git. The first-run flow must not require Git.

Chosen distribution strategy for this project:

1. **Phase 1 (current):** GitHub Releases + source archive with bootstrap script — machine runs via `wget` without Git.
2. **Phase 2 (future):** Build as `.deb` for proper `apt install` experience.
3. **Phase 3 (production):** Self-hosted or S3/Cloudflare R2 apt repository with GPG-signed packages.

## VM Recommendation

On Windows, use VirtualBox (free/open-source, low friction) or VMware Workstation Pro (free for personal/commercial since 2026). Hyper-V works but hardware passthrough for Linux desktop GUI is more complex.

## Wayland Support Research (2026-06-05)

### Background

Ubuntu 22.04 Desktop ships **GNOME on Wayland as the default session**. Users can select GNOME on Xorg at the login screen. Vending kiosks in this project currently force Xorg because the display/touchscreen stack depends entirely on X11 tools (`xrandr`, `xinput`).

This document records findings on what Wayland support would require.

---

### X11 vs Wayland Architecture

**X11 (current):**
- Xorg is the central authority for display output and input devices.
- `xrandr` controls outputs via the RandR X11 extension.
- `xinput` controls input devices via the XI2 X11 extension.
- `DISPLAY=:0` and `XAUTHORITY` grant access to the X server.
- `~/.xprofile` is sourced at X session login — used for persist-session.
- Xorg `InputClass` config (`/etc/X11/xorg.conf.d/`) persists touchscreen matrix across reboots.

**Wayland:**
- The compositor *is* the display server. No separate X server.
- Each compositor implements Wayland protocols differently — there is no single universal tool like `xrandr`/`xinput` that works across all compositors.
- `WAYLAND_DISPLAY=wayland-0` replaces `DISPLAY=:0`.
- `XDG_RUNTIME_DIR=/run/user/<uid>` holds the Wayland socket.

---

### Wayland Compositors Relevant to Ubuntu Kiosk

| Compositor | Default on | Display control | Touch control |
|---|---|---|---|
| GNOME / mutter | Ubuntu 22.04 Desktop | D-Bus `org.gnome.Mutter.DisplayConfig` | udev hwdb / gsettings |
| Sway | Not default (wlroots) | `wlr-randr` / `swaymsg output` | `swaymsg input` |
| KDE / KWin | Kubuntu | `kscreen-doctor` | KDE input settings |

---

### Display Rotation on Wayland

**GNOME Wayland:**
- Controlled via D-Bus interface `org.gnome.Mutter.DisplayConfig.ApplyMonitorsConfig`.
- Python tool `gnome-randr` wraps this D-Bus API with a CLI similar to `xrandr`.
- Installation: `pip install gnome-randr` or clone from GitHub.
- Example: `gnome-randr --output HDMI-1 --rotate left`
- No `xrandr` equivalent ships by default — requires extra dependency.

**Sway / wlroots:**
- Protocol: `zwlr_output_management_v1` (wlroots extension, not universal Wayland).
- Tool: `wlr-randr` (apt: `wlr-randr`).
- Example: `wlr-randr --output Virtual-1 --transform 270`
- Also available via `swaymsg output <name> transform 270`.

---

### Touchscreen Coordinate Mapping on Wayland

`xinput set-prop` **does not work on Wayland** — it talks to the X server which does not exist in a pure Wayland session.

**Option 1 — udev hwdb (compositor-agnostic, recommended):**

Works on both X11 and Wayland because it operates at the kernel/evdev level, before any compositor sees the events.

File: `/etc/udev/hwdb.d/61-vending-touchscreen.hwdb`
```
evdev:input:b<bustype>v<vendor>p<product>*
 EVDEV_ABS_00=<min>:<max>:<res>:<fuzz>:<flat>  # ABS_X
 EVDEV_ABS_01=<min>:<max>:<res>:<fuzz>:<flat>  # ABS_Y
 EVDEV_ABS_35=<min>:<max>:<res>:<fuzz>:<flat>  # ABS_MT_POSITION_X
 EVDEV_ABS_36=<min>:<max>:<res>:<fuzz>:<flat>  # ABS_MT_POSITION_Y
```

Apply: `systemd-hwdb update && udevadm trigger --subsystem-match=input`

**Limitation:** hwdb only remaps axis ranges (calibration), not rotation transformation matrix. Rotation still requires compositor-level mapping.

**Option 2 — GNOME gsettings / D-Bus:**
- Limited official support for touchscreen mapping in GNOME Wayland.
- No stable CLI equivalent of `xinput set-prop "Coordinate Transformation Matrix"`.

**Option 3 — Sway:**
```bash
swaymsg input <identifier> map_to_output <output>
swaymsg input <identifier> calibration_matrix <a> <b> <c> <d> <e> <f>
```
- Only works for Sway sessions.

---

### Session Persistence on Wayland

Current X11 approach uses `~/.xprofile` + retry script. On Wayland this file is not sourced.

**Wayland equivalents:**

| Method | Works on |
|---|---|
| `~/.profile` | Most display managers (GDM, LightDM) for login shells |
| `~/.config/autostart/<name>.desktop` | GNOME, KDE, most Wayland compositors |
| `~/.config/systemd/user/<name>.service` | systemd user session (compositor-agnostic) |
| Sway `~/.config/sway/config` | Sway only |

The most portable approach is a **systemd user service** (`Type=oneshot`) that runs after the graphical session starts (`After=graphical-session.target`).

---

### Tool Comparison: X11 vs Wayland

| Function | X11 (current) | GNOME Wayland | Sway/wlroots |
|---|---|---|---|
| Session detection | `XDG_SESSION_TYPE=x11` | `XDG_SESSION_TYPE=wayland` | `XDG_SESSION_TYPE=wayland` |
| List outputs | `xrandr --query` | D-Bus MutterDisplay | `wlr-randr` |
| Rotate display | `xrandr --rotate` | `gnome-randr` / D-Bus | `wlr-randr` / `swaymsg` |
| Map touchscreen | `xinput set-prop` | udev hwdb (partial) | `swaymsg input` |
| Persist rotation | `~/.xprofile` | autostart `.desktop` | sway config |
| Persist touch | `/etc/X11/xorg.conf.d/` | udev hwdb | udev hwdb / sway config |
| Device detection | `xinput list` | `libinput list-devices` | `libinput list-devices` |

---

### Recommended Path for Wayland Support

**Short-term (kiosk use case): Force X11 session**

Ubuntu 22.04 with GDM can be configured to default to Xorg without changing the desktop environment:

```bash
# Option 1: set default session via GDM config
sudo dpkg-reconfigure gdm3   # choose Xorg at prompt

# Option 2: environment variable (affects all users)
echo "GNOME_SHELL_SESSION_MODE=ubuntu-xorg" | sudo tee -a /etc/environment

# Option 3: user-level force
echo "export XDG_SESSION_TYPE=x11" >> ~/.profile
```

This is zero additional code, fully validated with the current stack, and appropriate for a kiosk device where session type is controlled by the operator.

**Medium-term: Compositor-agnostic touch via udev hwdb**

Extend `display persist-xorg` to also write a udev hwdb rule. This makes touchscreen calibration survive both X11 reboots and Wayland sessions without requiring compositor-specific tools.

**Long-term: Full Wayland backend**

Introduce a `DisplayBackend` abstraction with `X11Backend` and `WaylandBackend` implementations. The Wayland backend would detect the compositor (GNOME vs wlroots) and dispatch to the appropriate tool (`gnome-randr`, `wlr-randr`, or `swaymsg`). Session persistence would use a systemd user service instead of `~/.xprofile`.

Required new dependencies for Wayland:
- `dbus-python` or `dasbus` — for GNOME D-Bus calls
- `gnome-randr` — for GNOME output rotation
- `wlr-randr` — for wlroots output rotation
- `python3-evdev` — already considered for touchscreen testing

---

## Publication / Distribution Options

### GitHub Releases + bootstrap script (current)
Chosen for phase 1. Machine needs only `wget`, `tar`, Python. No Git required.

### `.deb` package + apt repository
Best long-term option for managed kiosk fleets. Can host on S3, Cloudflare R2, or GitHub Pages with GPG-signed metadata. Enables `apt upgrade` for updates.

### Launchpad PPA
Ubuntu ecosystem approach, requires Debian packaging and more build ceremony. Overkill for phase 1.

### Snap
Not suitable — snap confinement blocks the system-level operations this tool needs (apt repo management, Docker install, system config).
