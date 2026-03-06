"""
Migrate data from SQLite (db.sqlite3) to PostgreSQL.
Temporarily connects to SQLite, reads all app data, then writes to PostgreSQL.
"""
import os, sys, sqlite3, django

os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User, Group
from products.models import (
    BrandMateri, Lokasi, Dokumentator, LEDType, Requirement,
    ViewPhoto, cameratype, DocumentationRequest,
)

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3')

if not os.path.exists(SQLITE_PATH):
    print(f"ERROR: {SQLITE_PATH} not found!")
    sys.exit(1)

conn = sqlite3.connect(SQLITE_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== Migrating data from SQLite to PostgreSQL ===\n")

# --- 1. Groups ---
cur.execute("SELECT * FROM auth_group")
for row in cur.fetchall():
    Group.objects.get_or_create(id=row['id'], defaults={'name': row['name']})
print(f"Groups: {Group.objects.count()}")

# --- 2. Users ---
cur.execute("SELECT * FROM auth_user")
for row in cur.fetchall():
    if not User.objects.filter(username=row['username']).exists():
        User.objects.create(
            id=row['id'],
            username=row['username'],
            password=row['password'],  # already hashed
            first_name=row['first_name'],
            last_name=row['last_name'],
            email=row['email'],
            is_staff=row['is_staff'],
            is_active=row['is_active'],
            is_superuser=row['is_superuser'],
        )
print(f"Users: {User.objects.count()}")

# --- 3. User-Group memberships ---
cur.execute("SELECT * FROM auth_user_groups")
for row in cur.fetchall():
    try:
        user = User.objects.get(id=row['user_id'])
        group = Group.objects.get(id=row['group_id'])
        user.groups.add(group)
    except (User.DoesNotExist, Group.DoesNotExist):
        pass
print("User-group memberships restored")

# --- 4. Master data tables ---
SIMPLE_MODELS = {
    'products_brandmateri': BrandMateri,
    'products_lokasi': Lokasi,
    'products_dokumentator': Dokumentator,
    'products_ledtype': LEDType,
    'products_requirement': Requirement,
    'products_viewphoto': ViewPhoto,
    'products_cameratype': cameratype,
}

for table, Model in SIMPLE_MODELS.items():
    try:
        cur.execute(f"SELECT * FROM {table}")
        for row in cur.fetchall():
            Model.objects.get_or_create(id=row['id'], defaults={'name': row['name']})
        print(f"{Model.__name__}: {Model.objects.count()}")
    except Exception as e:
        print(f"{Model.__name__}: skipped ({e})")

# --- 5. DocumentationRequest ---
try:
    cur.execute("SELECT * FROM products_documentationrequest")
    for row in cur.fetchall():
        if not DocumentationRequest.objects.filter(id=row['id']).exists():
            dr = DocumentationRequest(
                id=row['id'],
                submitted_by_id=row['submitted_by_id'],
                brand_materi_id=row['brand_materi_id'],
                lokasi_id=row['lokasi_id'],
                jenis_led_id=row['jenis_led_id'],
                tanggal=row['tanggal'],
                note=row['note'],
                pic_pemohon=row['pic_pemohon'],
                status=row['status'],
            )
            # Handle created_at
            if 'created_at' in row.keys():
                dr.created_at = row['created_at']
            dr.save()
    print(f"DocumentationRequest: {DocumentationRequest.objects.count()}")
except Exception as e:
    print(f"DocumentationRequest: error ({e})")

# --- 6. M2M relationships ---
M2M_TABLES = {
    'products_documentationrequest_requirements': ('documentationrequest_id', 'requirement_id'),
    'products_documentationrequest_view_photo': ('documentationrequest_id', 'viewphoto_id'),
    'products_documentationrequest_jenis_kamera': ('documentationrequest_id', 'cameratype_id'),
    'products_documentationrequest_pelaksana': ('documentationrequest_id', 'dokumentator_id'),
}

M2M_FIELDS = {
    'products_documentationrequest_requirements': 'requirements',
    'products_documentationrequest_view_photo': 'view_photo',
    'products_documentationrequest_jenis_kamera': 'jenis_kamera',
    'products_documentationrequest_pelaksana': 'pelaksana',
}

for table, (fk_col, related_col) in M2M_TABLES.items():
    field_name = M2M_FIELDS[table]
    try:
        cur.execute(f"SELECT * FROM {table}")
        count = 0
        for row in cur.fetchall():
            try:
                dr = DocumentationRequest.objects.get(id=row[fk_col])
                getattr(dr, field_name).add(row[related_col])
                count += 1
            except DocumentationRequest.DoesNotExist:
                pass
        print(f"M2M {field_name}: {count} links")
    except Exception as e:
        print(f"M2M {field_name}: skipped ({e})")

conn.close()

# Reset PostgreSQL sequences
from django.db import connection
with connection.cursor() as cursor:
    tables = [
        'auth_user', 'auth_group', 'products_brandmateri', 'products_lokasi',
        'products_dokumentator', 'products_ledtype', 'products_requirement',
        'products_viewphoto', 'products_cameratype', 'products_documentationrequest',
    ]
    for table in tables:
        try:
            cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}")
        except Exception:
            pass

print("\n=== Migration complete! ===")
