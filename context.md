# Session Context — vending-auto-setup

วันที่: 2026-06-05  
Branch: main  
เครื่องทดสอบ: Ubuntu 22.04 LTS Desktop ใน VirtualBox (user: first)

---

## สิ่งที่ทำในเซสชันนี้

### 1. Fix: `sudo vas check` แสดงผลผิด (commits d2cb321, 60e222b)

**ปัญหาที่พบ:**
- `sudo vas check` → `[Session] WARN Display unknown (not detected)` เพราะ sudo ลบ `XDG_SESSION_TYPE` ออกจาก env
- `sudo vas check` → `[Display Config]` ดูผิด path เป็น `/root/.xprofile` แทน `/home/first/.xprofile` เพราะ `Path.home()` เป็น module-level constant
- `vas check` → Script WARN "not executable" เพราะ server (รันเป็น root) เขียนไฟล์แต่ chmod set execute bit ให้แค่ root

**แก้ไขใน `src/status.py`:**
- เพิ่ม `_effective_home()` ที่อ่าน `SUDO_USER` จาก env แล้ว resolve home จาก `pwd.getpwnam()` แทน `Path.home()`
- เพิ่ม `_effective_home_config_path()` / `_effective_home_script_path()` สำหรับ call ที่ run time
- เปลี่ยน `collect_display_session_config_status()` / `_script_status()` ให้รับ `path=None` และ resolve path ตอน call
- เพิ่ม `_scan_loginctl_sessions()` — fallback scan ทุก session จาก `loginctl list-sessions` โดยไม่ต้องพึ่ง `XDG_SESSION_ID`

**แก้ไขใน `src/display.py`:**
- `persist_session()` เปลี่ยน default `path`/`script_path` เป็น `None` และ resolve ตอน call
- chmod จาก `S_IXUSR` เป็น `755` (`S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH`)
- เพิ่ม `_chown_to_effective_user()` — chown ไฟล์ไปให้ `SUDO_USER` หลัง server (root) เขียนไฟล์ใน home user

**แก้ไขใน `src/reset.py`:**
- `reset_display_config()` ใช้ `_effective_home_*_path()` แทน constants

---

### 2. Feature: Touchscreen detection ด้วย udevadm + `vas display list-touch` (commit b05ec4c)

**ปัญหาเดิม:**
- `parse_xinput_touch_devices()` กรองด้วย "touch" ใน name เท่านั้น — ไม่น่าเชื่อถือ
- ไม่มีทาง list touchscreen พร้อม xinput ID

**เพิ่มใน `src/display.py`:**
```
TouchDevice(name, xinput_id)          # dataclass
parse_xinput_device_map(output)        # parse xinput list → {name: id}
get_udevadm_touchscreen_names(runner)  # อ่านชื่อ touchscreen จาก udevadm kernel database
list_touch_devices(runner, display)    # combine udevadm + xinput → tuple[TouchDevice]
DisplayConfigurator.print_touch_devices()
```

**Logic การ detect:**
1. ใช้ `udevadm info --export-db` → filter block ที่มี `ID_INPUT_TOUCHSCREEN=1` → ได้ชื่อ
2. Cross-ref กับ `xinput list` → ได้ xinput ID
3. Fallback: filter xinput ด้วย "touch" ใน name

**เพิ่มใน `src/server.py`:**
- `DisplayDevices.touch_devices` เปลี่ยนเป็น `tuple[TouchDevice, ...]`
- `collect_display_devices()` ใช้ udevadm-based detection
- `/api/display/devices` return `{"name": str, "id": int|null}` แทน string
- `validate_display_apply()` ใช้ `touch not in (d.name for d in devices.touch_devices)`

**เพิ่มใน `src/cli.py`:**
- `vas display list-touch [--display :0] [--xauthority PATH]`

**เปลี่ยนใน `src/web/templates/display.html`:**
- Touchscreen dropdown แสดง `Name (id: N)`
- JS `replaceOptions()` รองรับ `{name, id}` objects จาก API

---

### 3. Feature: Display Status Bar + Config File Viewer (commit f848e43)

**เพิ่มใน `src/server.py`:**
- `display_settings()` ส่ง `session`, `display_config`, `display_script`, `xorg_touchscreen` ไปยัง template
- `/api/display/config-content?key=<key>` endpoint อ่านไฟล์ config พร้อม allowlist:
  - `xprofile` → `~/.xprofile`
  - `display_script` → `~/.config/vending-auto-setup/display-session.sh`
  - `xorg_touchscreen` → `/etc/X11/xorg.conf.d/99-vending-touchscreen.conf`
- `_allowed_config_paths()` helper

**เปลี่ยนใน `src/web/templates/display.html`:**
- Status bar แสดง:
  - แถวบน: Session (X11/Wayland + OK/WARN), Monitors (chip ต่อจอ), Touchscreens (chip + id)
  - แถวล่าง: Config file statuses (.xprofile, display-session.sh, Xorg) พร้อมปุ่ม View
- Config File Viewer: panel แสดง path + เนื้อหาไฟล์ inline (max-height 260px, scrollable)

---

## สถานะไฟล์หลัก

| ไฟล์ | สถานะ |
|---|---|
| `src/status.py` | แก้ home path + session detection |
| `src/display.py` | เพิ่ม TouchDevice, udevadm detection, chmod/chown fix |
| `src/server.py` | DisplayDevices → TouchDevice, API updates, config-content endpoint |
| `src/reset.py` | ใช้ _effective_home_*_path() |
| `src/cli.py` | เพิ่ม `display list-touch` |
| `src/web/templates/display.html` | Status bar + Config viewer |
| `tests/test_server.py` | อัปเดต tests ตาม TouchDevice |

---

## Known Issues / ข้อควรระวัง

- git index อาจ corrupt ได้ใน sandbox เมื่อ commit ผ่าน Cowork — ให้ commit จากเครื่อง VM โดยตรง
- lock files (`.git/HEAD.lock`, `.git/index.lock`) จาก sandbox อาจค้างอยู่ใน Windows NTFS — ลบด้วย `del` จาก CMD/PowerShell
- `display-session.sh` ต้องมี executable bit — ถ้าถูกสร้างโดย server (root) จะ chown ให้ user จริงอัตโนมัติ
- `vas display list-touch` ต้องรันใน X session หรือส่ง `--display :0` เพื่อให้ xinput ทำงานได้

---

## สิ่งที่ควรทำต่อ (จาก TODO.md + session นี้)

- เพิ่ม command `display configure` แบบ guided (ถาม output, touch, rotate ทีละขั้น)
- เพิ่ม auto-select touch device ถ้าเจอแค่ตัวเดียว
- เพิ่ม log ของ `display-session.sh` ดูได้จาก web UI
- เพิ่ม check Docker daemon active + user อยู่ใน docker group
- ทำ `.deb` package หลัง CLI stable
