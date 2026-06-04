# บันทึกการรีเสิร์ช

## Flow bootstrap ที่แนะนำ

Ubuntu 22.04 Desktop ที่ติดตั้งใหม่มักมี Python 3.10 อยู่แล้ว แต่ Git อาจยังไม่ได้ติดตั้ง ดังนั้น flow สำหรับการรันครั้งแรกไม่ควรบังคับให้ต้องมี Git ก่อน

ลำดับการเผยแพร่โปรแกรมที่เลือกสำหรับโปรเจกต์นี้:

1. ช่วงแรก: ใช้ GitHub Releases หรือ source archive พร้อม bootstrap script เพื่อให้เครื่อง Ubuntu ใหม่รันได้โดยไม่ต้องมี Git
2. ช่วงต่อไป: ถ้าต้องการให้ติดตั้งด้วย `apt install` จริง ค่อย build เป็น `.deb`
3. ช่วง production ที่ต้องการ update ผ่าน apt: ค่อยย้ายไป managed apt hosting หรือ self-hosted apt repository

## ทางเลือก

### GitHub Releases พร้อม bootstrap script

นี่คือทางเลือกที่เลือกใช้ใน phase แรก โปรแกรมจะถูก publish ไว้บน GitHub และเครื่องปลายทางจะรัน script ผ่าน `curl`:

```bash
curl -fsSL https://example.com/vending-auto-setup/install.sh | sudo bash
```

ตัว script จะดาวน์โหลด source archive จาก GitHub, แตกไฟล์ด้วย `tar`, แล้วรัน Python module โดยใช้ `PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m vending_auto_setup install
```

วิธีนี้เหมาะกับช่วงแรกที่สุด เพราะต้องการแค่ `curl`, `tar`, Python และ internet โดยไม่ต้องมี Git ข้อเสียคือยังไม่ใช่ apt repository จริง ดังนั้นการ update จะยังไม่ได้ใช้ `apt upgrade`

### `.deb` package พร้อม apt repository

วิธีนี้เหมาะที่สุดในระยะยาวสำหรับการเตรียมเครื่องตู้ vending เพราะ command แรกจะหน้าตาเหมือนการติดตั้ง package ปกติของ Ubuntu:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://example.com/vending-auto-setup.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/vending-auto-setup.gpg
echo "deb [signed-by=/etc/apt/keyrings/vending-auto-setup.gpg] https://example.com/apt stable main" | sudo tee /etc/apt/sources.list.d/vending-auto-setup.list
sudo apt update
sudo apt install vending-auto-setup
sudo vending-auto-setup install
```

สำหรับใช้งานภายใน apt repository สามารถ host บน S3, Cloudflare R2, GitHub Pages หรือ static HTTPS host อื่นได้ ถ้ามีการ generate และ sign repository metadata ให้ถูกต้อง

### Launchpad PPA

Launchpad PPA ใช้ publish Ubuntu apt repository จาก Ubuntu source package ที่ upload เข้า Launchpad วิธีนี้ใกล้กับ ecosystem ของ Ubuntu มากกว่า แต่ต้องทำ Debian packaging และมีขั้นตอนหนักกว่า GitHub release สำหรับ phase 1

### Snap

Snap ติดตั้งง่ายบน Ubuntu Desktop แต่ tool นี้ต้องแก้ host ด้วยสิทธิ์สูง เช่น เพิ่ม apt repository, ลบ package เก่า, ติดตั้ง Docker และแก้ system configuration ดังนั้น snap confinement แบบปกติไม่เหมาะกับ installer ตัวนี้

## คำแนะนำเรื่อง VM

บน Windows ให้ใช้ VMware Workstation Pro หรือ VirtualBox

- VMware Workstation Pro ตอนนี้ฟรีสำหรับ personal, educational และ commercial use ตาม FAQ/blog ของ VMware/Broadcom ในปี 2026 แต่อาจมี friction เรื่อง account หรือขั้นตอน download
- VirtualBox เป็น free/open-source ดาวน์โหลดง่าย และเพียงพอสำหรับทดสอบการติดตั้ง Ubuntu Desktop
- Hyper-V เป็นอีกทางเลือกบน Windows Pro/Enterprise แต่ hardware passthrough และ UX ของ Linux desktop อาจยุ่งยากกว่า

สำหรับโปรเจกต์นี้ VirtualBox เป็น default ที่ friction ต่ำสุด ส่วน VMware Workstation Pro ใช้ได้ดีถ้ามีติดตั้งอยู่แล้ว
