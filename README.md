# 🎓 Seminar Portal

**Seminar Portal** adalah platform berbasis web untuk manajemen kegiatan seminar, workshop, dan lomba. Website ini menghubungkan **Organizer** (penyelenggara acara) dengan **Peserta** dalam satu ekosistem yang terintegrasi.

Dibangun menggunakan **Django Framework**, sistem ini dilengkapi dengan fitur modern seperti tiket QR Code, sertifikat otomatis, dan integrasi notifikasi (WhatsApp/Telegram/Email).

---

## ✨ Fitur Unggulan

### 👥 Untuk Peserta (Public)
* **Login Praktis:** Masuk menggunakan akun **Google** (OAuth2).
* **Pendaftaran Mudah:** Formulir pendaftaran event dengan upload bukti bayar.
* **Tiket QR Code:** Tiket unik berbasis UUID yang digenerate otomatis.
* **Cek Tiket (Guest):** Fitur cari tiket/QR code tanpa perlu login (cukup input email).
* **Dashboard Peserta:** Riwayat kegiatan yang diikuti.
* **E-Certificate:** Download sertifikat PDF otomatis setelah acara selesai dan status valid.

### 📊 Untuk Organizer (Penyelenggara)
* **Manajemen Event:** Buat, edit, dan pantau status event (Pending/Active/Finished).
* **Analitik Dashboard:** Ringkasan total peserta dan estimasi pendapatan.
* **Verifikasi Peserta:** Validasi bukti pembayaran peserta (Pending -> Lunas).
* **Scan QR Code:** Validasi kehadiran peserta di lokasi acara menggunakan kamera HP.
* **Export Data:** Download data peserta ke format **Excel (.xlsx)**.
* **Blast Email:** Kirim pengumuman ke seluruh peserta event sekaligus.
* **Share Event:** Fitur salin link pendaftaran dengan format WhatsApp yang rapi.

### 🛡️ Untuk Admin (Superuser)
* **Validasi Event:** Menyetujui atau menolak event yang diajukan Organizer sebelum tayang.
* **Manajemen User:** Mengelola pengguna dan hak akses.
* **Blacklist System:** Memblokir email tertentu agar tidak bisa mendaftar.
* **Notifikasi Real-time:** Menerima notifikasi via Telegram/Email saat ada event baru.

---

## 🛠️ Teknologi yang Digunakan

* **Backend:** Django 5.x (Python)
* **Database:** SQLite (Dev) / PostgreSQL (Production)
* **Frontend:** Bootstrap 5, HTML5, CSS3
* **Auth:** Django Allauth (Google Login)
* **Fitur Tambahan:**
    * `qrcode` (Generate Tiket)
    * `reportlab` (Generate PDF Sertifikat)
    * `openpyxl` (Export Excel)
    * `python-decouple` (Manajemen Environment Variables)
    * `whitenoise` (Static files di Production)

---