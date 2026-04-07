# Django ITS

Project ini tetap bisa jalan tanpa `.env` dengan SQLite lokal, tetapi untuk deployment yang memakai PostgreSQL 12 sebaiknya gunakan konfigurasi PostgreSQL dan seri Django `4.2.x`. Seri `Django 5.2` resmi mendukung PostgreSQL `14+`, jadi kurang cocok jika server Anda masih di PostgreSQL 12.

## Kompatibilitas PostgreSQL 12

- `requirements.txt` sekarang dipasang ke `Django==4.2.29`
- `psycopg2-binary==2.9.11` tetap aman dipakai untuk PostgreSQL 12
- Jika nanti server PostgreSQL sudah di-upgrade ke `14+`, baru aman naik lagi ke Django `5.2+`
- Karena support Django `4.2` berakhir di April 2026, upgrade PostgreSQL server sebaiknya jadi langkah berikutnya

## Setup local dengan PostgreSQL

1. Buat virtual environment dan install dependency:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Jika Anda memakai PowerShell dan ingin masuk ke virtualenv dulu:

```powershell
.venv\Scripts\Activate.ps1
```

Kalau sudah aktif, prompt biasanya berubah menjadi `(.venv)` dan Anda bisa memakai `python ...` biasa.

2. Buat database PostgreSQL:

```sql
CREATE DATABASE djangtest;
```

3. Buat `.env` dari `.env.example`, lalu isi salah satu format berikut:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/djangtest
```

atau:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=djangtest
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
```

4. Jalankan migrasi:

```powershell
.venv\Scripts\python manage.py migrate
```

5. Seed data awal jika dibutuhkan:

```powershell
.venv\Scripts\python seed_fresh_install.py
```

6. Jalankan server:

```powershell
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

Atau pakai helper PowerShell supaya tidak salah interpreter:

```powershell
.\dev.ps1 migrate
.\dev.ps1 seed
.\dev.ps1 runserver
```

## Pindah dari SQLite ke PostgreSQL

Kalau data lama masih ada di `db.sqlite3`, urutannya:

1. Backup dulu file SQLite lama.
2. Arahkan `.env` ke PostgreSQL.
3. Jalankan `manage.py migrate` untuk membuat schema di PostgreSQL.
4. Jalankan script migrasi data:

```powershell
.venv\Scripts\python migrate_data.py
```

Script `migrate_data.py` membaca data dari `db.sqlite3` lalu menulisnya ke PostgreSQL.

## Setup di server PostgreSQL 12

Langkah server pada dasarnya sama dengan local:

1. Install dependency dari `requirements.txt`
2. Pastikan `.env` mengarah ke PostgreSQL server
3. Jalankan `manage.py migrate`
4. Jalankan `seed_fresh_install.py` bila server masih fresh install
5. Jalankan aplikasi lewat WSGI/ASGI sesuai web server Anda

## Catatan penting di Windows

Jangan pakai `py manage.py ...` atau `python seed_fresh_install.py` jika interpreter aktif masih Python global yang membawa Django lain. Untuk project ini, lebih aman gunakan:

```powershell
.\dev.ps1 runserver
.\dev.ps1 seed
```

atau langsung:

```powershell
.venv\Scripts\python manage.py runserver
.venv\Scripts\python seed_fresh_install.py
```

## Default tanpa `.env`

- Database: SQLite di `db.sqlite3`
- Static: disajikan dari folder `static`
- Media: disajikan dari folder `media`

Mode ini tetap berguna untuk percobaan cepat lokal, tetapi bukan pilihan yang disarankan bila target akhirnya PostgreSQL 12 di server.
