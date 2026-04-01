# Django ITS

Project ini sekarang bisa dijalankan tanpa konfigurasi manual tambahan. Jika tidak ada `.env`, aplikasi akan memakai SQLite lokal, `ALLOWED_HOSTS=*`, dan file `static/media` dilayani langsung oleh Django supaya bisa dipindah ke lokal maupun server dengan langkah minimum.

## Jalankan di mesin baru

1. Buat virtual environment dan install dependency:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

2. Jalankan migrasi:

```powershell
.venv\Scripts\python manage.py migrate
```

3. Buat akun admin jika dibutuhkan:

```powershell
.venv\Scripts\python manage.py createsuperuser
```

4. Jalankan server:

```powershell
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

## Default tanpa `.env`

- Database: SQLite di `db.sqlite3`
- Host: menerima semua host
- Static: disajikan dari folder `static`
- Media: disajikan dari folder `media`

Dengan mode default ini, setelah code dan dependency ada di server, Anda cukup `migrate` lalu jalankan aplikasinya.

## Override opsional

Kalau nanti ingin pakai PostgreSQL / MySQL atau membatasi host, buat file `.env` berdasarkan `.env.example`.
