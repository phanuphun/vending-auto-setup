# Vending Auto Setup

โปรเจกต์นี้เป็น CLI สำหรับเตรียมเครื่อง Ubuntu 22.04 LTS Desktop ที่ใช้กับตู้ vending โดยเป้าหมายคือให้เครื่องใหม่สามารถติดตั้ง software พื้นฐานและตั้งค่าจอ/touchscreen ได้ด้วยคำสั่งให้น้อยที่สุด

## สิ่งที่โปรแกรมทำได้ตอนนี้

Phase 1:

- ติดตั้ง Docker Engine จาก official Docker apt repository
- ติดตั้ง Node.js จาก NodeSource apt repository
- ติดตั้ง Git จาก Ubuntu apt package
- ตรวจสถานะ Git, Node.js, npm, Docker

Phase 2 ที่เริ่มทำแล้ว:

- ตรวจว่า session ปัจจุบันเป็น X11 หรือ Wayland
- ตรวจว่า Xorg touchscreen config ถูกตั้งไว้หรือยัง
- ตรวจว่า display session script ถูกตั้งไว้หรือยัง
- หมุนจอด้วย `xrandr`
- map touchscreen coordinate ด้วย `xinput`
- persist touchscreen matrix ผ่าน Xorg config
- persist display rotation ผ่าน `.xprofile` ที่เรียก retry script

Phase 3 WireGuard ที่เริ่มทำแล้ว:

- ติดตั้ง package `wireguard`
- สร้าง template config เช่น `wg0.conf`
- validate config โดยไม่พิมพ์ค่า secret key ลง output
- save config เข้า app storage โดยยังไม่ apply จริง
- sync config ไปที่ `/etc/wireguard/<interface>.conf` และ enable/restart service
- เก็บ history ของ config ที่ sync แล้ว
- อ่าน history แบบ mask secret เป็นค่า default
- unsync เพื่อนำ config ที่ใช้งานอยู่ออกและ disable service

## Bootstrap บน Ubuntu ใหม่โดยไม่ต้องมี Git

เครื่อง Ubuntu ใหม่อาจยังไม่มี Git ดังนั้น flow แรกจะใช้ `curl` หรือ `wget` เพื่อโหลด bootstrap script จาก GitHub

ตรวจ OS อย่างเดียว:

```bash
wget -qO- https://raw.githubusercontent.com/phanuphun/vending-auto-setup/main/scripts/install.sh | VENDING_AUTO_SETUP_ARGS=about-os bash
```

ตรวจสถานะทั้งหมด:

```bash
wget -qO- https://raw.githubusercontent.com/phanuphun/vending-auto-setup/main/scripts/install.sh | VENDING_AUTO_SETUP_ARGS=check bash
```

ติดตั้ง Git, Node.js, npm, Docker จริง:

```bash
wget -qO- https://raw.githubusercontent.com/phanuphun/vending-auto-setup/main/scripts/install.sh | sudo bash
```

แนะนำให้ snapshot VM ก่อนรัน install จริง เพราะคำสั่งนี้จะแก้ apt repository และติดตั้ง package ลงเครื่อง

## ติดตั้งแบบ local development

ถ้า clone repo มาแล้ว:

```bash
cd ~/vending-auto-setup
PYTHONPATH=src python3 -m vending_auto_setup check
```

ถ้าต้องการติดตั้ง package ใน virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

หลังติดตั้ง package แล้วจะใช้ command ได้:

```bash
vending-auto-setup check
vending-status
```

## ตรวจสถานะเครื่อง

คำสั่ง:

```bash
PYTHONPATH=src python3 -m vending_auto_setup check
```

ตัวอย่าง output:

```text
Vending Auto Setup Status

[Session]
OK      Display    x11 (XDG_SESSION_TYPE)

[Display Config]
OK      Session    configured (/home/first/.xprofile)
OK      Script     configured (/home/first/.config/vending-auto-setup/display-session.sh)

[Touchscreen]
OK      Xorg       configured (/etc/X11/xorg.conf.d/99-vending-touchscreen.conf)

[Core Tools]
OK      Git        git version 2.34.1
OK      Node.js    v22.22.3
OK      npm        10.9.8
OK      Docker     Docker version 29.5.3, build d1c06ef
```

ความหมาย:

- `[Session]` ตรวจว่า login เป็น X11 หรือไม่ ถ้าเป็น Wayland จะขึ้น `WARN`
- `[Display Config] Session` ตรวจว่า `~/.xprofile` มี managed block ของโปรแกรมหรือยัง
- `[Display Config] Script` ตรวจว่า retry script มีอยู่และ executable หรือยัง
- `[Touchscreen] Xorg` ตรวจว่า `/etc/X11/xorg.conf.d/99-vending-touchscreen.conf` มี signature หรือยัง
- `[Core Tools]` ตรวจ Git, Node.js, npm, Docker

## ตรวจ X11, xrandr, xinput

ดู output จอและ input device:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display status --display :0
```

คำสั่งนี้จะรัน:

```bash
xrandr --query
xinput list
```

ถ้ารันจาก user ที่ login อยู่ใน GUI ปกติ `--display :0` มักจะพอ แต่ถ้ารันจาก SSH หรือ root อาจต้องใช้ `XAUTHORITY` เพิ่ม ซึ่งจะทำเป็น flow แยกในอนาคต

## จำลอง touchscreen ใน VirtualBox

ถ้าไม่มีจอสัมผัสจริง สามารถสร้าง virtual touchscreen ใน Ubuntu guest ด้วย `uinput`

ติดตั้ง dependency:

```bash
sudo apt update
sudo apt install -y python3-evdev
```

เปิด virtual touchscreen ค้างไว้:

```bash
sudo python3 scripts/dev/virtual_touchscreen.py --width 1920 --height 1080
```

เปิดอีก terminal แล้วเช็ก:

```bash
xinput list
```

ควรเห็น:

```text
Vending Virtual Touchscreen
```

ดู properties:

```bash
xinput list-props "Vending Virtual Touchscreen"
```

หรือถ้ารู้ id เช่น `13`:

```bash
xinput list-props 13
```

## หมุนจอและ map touchscreen แบบ runtime

คำสั่งนี้มีผลทันทีใน session ปัจจุบัน:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display apply \
  --display :0 \
  --output Virtual1 \
  --touch "Vending Virtual Touchscreen" \
  --rotate left
```

สิ่งที่คำสั่งนี้ทำ:

```bash
xrandr --output Virtual1 --rotate left
xinput set-prop "Vending Virtual Touchscreen" "Coordinate Transformation Matrix" 0 -1 1 1 0 0 0 0 1
```

กลับจอเป็นปกติ:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display apply \
  --display :0 \
  --output Virtual1 \
  --touch "Vending Virtual Touchscreen" \
  --rotate normal
```

ค่าที่ใช้ได้:

- `normal`
- `left`
- `right`
- `inverted`

Matrix ที่ใช้:

```text
normal   1 0 0 0 1 0 0 0 1
right    0 1 0 -1 0 1 0 0 1
left     0 -1 1 1 0 0 0 0 1
inverted -1 0 1 0 -1 1 0 0 1
```

## Persist touchscreen ผ่าน Xorg

คำสั่งนี้เขียน config ของ touchscreen matrix ลง Xorg:

```bash
sudo PYTHONPATH=src python3 -m vending_auto_setup display persist-xorg \
  --touch "Vending Virtual Touchscreen" \
  --rotate left
```

ไฟล์ที่ถูกสร้าง:

```text
/etc/X11/xorg.conf.d/99-vending-touchscreen.conf
```

ตัวอย่างเนื้อหา:

```conf
# vending-auto-config: touchscreen-xorg
# Managed by vending-auto-setup. Manual edits may be overwritten.
Section "InputClass"
    Identifier "vending-touchscreen-calibration"
    MatchProduct "Vending Virtual Touchscreen"
    Option "CalibrationMatrix" "0 -1 1 1 0 0 0 0 1"
EndSection
```

เหตุผลที่ใช้ Xorg config:

- Xorg จะ match device จาก `MatchProduct`
- เหมาะกับกรณี cold boot ที่ touchscreen device อาจโหลดช้ากว่า session
- เป็น config หลักของ touchscreen matrix

ข้อจำกัด:

- ไฟล์นี้ไม่ได้หมุนจอ
- การหมุนจอต้องใช้ `xrandr` ซึ่งต้องทำใน X session

## Persist display rotation ผ่าน session script

คำสั่งนี้เขียน config ให้ user session เรียก script ตอน login:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display persist-session \
  --display :0 \
  --output Virtual1 \
  --touch "Vending Virtual Touchscreen" \
  --rotate left
```

ห้ามใช้ `sudo` กับคำสั่งนี้ เพราะต้องเขียนไฟล์ของ user ที่ login GUI อยู่ ไม่ใช่ `/root`

สิ่งที่ถูกสร้าง:

```text
~/.xprofile
~/.config/vending-auto-setup/display-session.sh
```

หน้าที่ของ `~/.xprofile`:

```text
เป็นจุดเริ่มตอน login เข้า X session
เรียก display-session.sh แบบ background
```

หน้าที่ของ `display-session.sh`:

```text
รอให้จอ output เช่น Virtual1 พร้อม
ถ้ายังไม่พร้อมจะ retry
เมื่อพร้อมแล้วรัน xrandr เพื่อหมุนจอ
รอให้ touchscreen พร้อม
ถ้ายังไม่พร้อมจะ retry
เมื่อพร้อมแล้วรัน xinput set-prop เพื่อ map coordinate
```

เหตุผลที่ไม่เขียน `xrandr` ตรง ๆ ใน `.xprofile`:

- ถ้า boot ช้า คำสั่งอาจรันก่อนจอหรือ touchscreen พร้อม
- ถ้าพลาดจะไม่ลองใหม่
- แยกเป็น script แล้ว debug ง่ายกว่า
- เพิ่ม retry/log ได้ในอนาคต

## Flow ที่แนะนำสำหรับเครื่องจริง

1. ตรวจว่าเป็น X11:

```bash
PYTHONPATH=src python3 -m vending_auto_setup check
```

2. ดูชื่อจอและ touchscreen:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display status --display :0
```

3. ลอง apply runtime ก่อน:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display apply \
  --display :0 \
  --output Virtual1 \
  --touch "Vending Virtual Touchscreen" \
  --rotate left
```

4. ถ้าถูกต้องแล้ว persist Xorg:

```bash
sudo PYTHONPATH=src python3 -m vending_auto_setup display persist-xorg \
  --touch "Vending Virtual Touchscreen" \
  --rotate left
```

5. Persist session script:

```bash
PYTHONPATH=src python3 -m vending_auto_setup display persist-session \
  --display :0 \
  --output Virtual1 \
  --touch "Vending Virtual Touchscreen" \
  --rotate left
```

6. ตรวจสถานะ:

```bash
PYTHONPATH=src python3 -m vending_auto_setup check
```

7. Reboot เพื่อทดสอบ cold boot:

```bash
sudo reboot
```

หลัง login กลับมา จอควรถูกหมุน และ touchscreen ควรถูก map ตามค่าที่ตั้งไว้

## WireGuard

WireGuard flow แยก `save` ออกจาก `sync` ชัดเจน:

- `save` คือเก็บ config เข้า app storage แต่ยังไม่นำไปใช้งานจริง
- `sync` คือเขียน config ไปที่ `/etc/wireguard/<interface>.conf` แล้ว enable/restart service จริง

ติดตั้ง WireGuard:

```bash
sudo vending-auto-setup wireguard install
```

สร้าง template config:

```bash
vending-auto-setup wireguard init-config --name wg0 --output ./wg0.conf
```

แก้ค่าใน `./wg0.conf` ให้ครบ แล้ว validate:

```bash
vending-auto-setup wireguard validate --config ./wg0.conf
```

บันทึก config เข้า app storage โดยยังไม่ apply:

```bash
vending-auto-setup wireguard save --name wg0 --config ./wg0.conf
```

นำ config ที่ save ไว้ไปใช้จริง:

```bash
sudo vending-auto-setup wireguard sync --name wg0
```

สิ่งที่ `sync` ทำ:

- validate config อีกรอบ
- backup `/etc/wireguard/wg0.conf` เดิมก่อนเขียนทับ ถ้ามี
- เขียน `/etc/wireguard/wg0.conf`
- ตั้ง permission เป็น `600`
- บันทึก snapshot เข้า history
- รัน `systemctl enable wg-quick@wg0`
- รัน `systemctl restart wg-quick@wg0`

ตรวจสถานะ:

```bash
vending-auto-setup wireguard status --name wg0
```

ดู history config ที่เคย sync:

```bash
vending-auto-setup wireguard history --name wg0
```

อ่าน config จาก history แบบปิด secret key เป็นค่า default:

```bash
vending-auto-setup wireguard show --name wg0 --id 20260604T120000Z-sync
```

ถ้าจำเป็นต้องดูค่า secret จริง ให้ระบุ flag ชัดเจน:

```bash
vending-auto-setup wireguard show --name wg0 --id 20260604T120000Z-sync --reveal-secrets
```

นำ config ที่ sync ออก:

```bash
sudo vending-auto-setup wireguard unsync --name wg0
```

คำสั่งนี้จะ `systemctl disable --now wg-quick@wg0`, backup config ปัจจุบันเข้า history แล้วลบ `/etc/wireguard/wg0.conf`

ค่า default ของ app storage อยู่ที่:

```text
~/.config/vending-auto-setup/wireguard
```

ถ้ารันผ่าน `sudo` โปรแกรมจะพยายามใช้ home ของ `SUDO_USER` เพื่อให้ `sync` เห็น config ที่ user เคย `save` ไว้

ข้อควรระวัง:

- ห้าม commit private key หรือ preshared key ลง repo
- output ปกติจะไม่พิมพ์ค่า `PrivateKey` และ `PresharedKey`
- history เป็น read-only ผ่าน CLI ถ้าต้องแก้ config ให้สร้าง/แก้ไฟล์ใหม่ แล้ว `save` และ `sync` ใหม่

## Troubleshooting

ถ้า Terminal เปิดไม่ได้ใน VirtualBox:

```text
อาจเกิดจาก locale ไม่เป็น UTF-8
```

แก้ `/etc/default/locale` ให้มี:

```text
LANG=en_US.UTF-8
LANGUAGE=en_US:en
LC_ALL=en_US.UTF-8
```

แล้วรัน:

```bash
sudo locale-gen --purge
sudo reboot
```

ถ้า `xinput` ไม่เห็น touchscreen:

```bash
xinput list
```

ตรวจว่า script จำลอง touchscreen ยังรันค้างอยู่หรือไม่:

```bash
sudo python3 scripts/dev/virtual_touchscreen.py --width 1920 --height 1080
```

ถ้า `xrandr` ไม่เจอ output:

```bash
xrandr --query
```

ใช้ชื่อ output ที่ขึ้นว่า `connected` เช่น `Virtual1`, `HDMI-1`, `DP-1`

ถ้า Docker รันโดยไม่ใช้ sudo ไม่ได้:

```bash
sudo usermod -aG docker $USER
sudo reboot
```

## Configuration

ค่า default อยู่ใน:

```text
src/vending_auto_setup/config.py
```

- `node_major` ค่า default คือ `22`
- Docker ใช้ package ล่าสุดจาก Docker official apt repository ถ้าไม่ระบุ `--docker-version`
- Git ใช้ package จาก Ubuntu apt repository ถ้าไม่ระบุ `--git-version`
