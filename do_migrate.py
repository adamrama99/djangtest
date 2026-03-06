import sqlite3, os
from django.contrib.auth.models import User, Group
from products.models import BrandMateri, Lokasi, Dokumentator, LEDType, Requirement, ViewPhoto, cameratype, DocumentationRequest

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath('manage.py')), 'db.sqlite3')
print(f"SQLite path: {SQLITE_PATH}")
print(f"Exists: {os.path.exists(SQLITE_PATH)}")

conn = sqlite3.connect(SQLITE_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

for table, Model in [('products_ledtype', LEDType), ('products_requirement', Requirement), ('products_viewphoto', ViewPhoto), ('products_cameratype', cameratype), ('products_brandmateri', BrandMateri), ('products_lokasi', Lokasi)]:
    try:
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()
        created = 0
        for r in rows:
            obj, was_created = Model.objects.get_or_create(id=r['id'], defaults={'name': r['name']})
            if was_created:
                created += 1
        print(f"{Model.__name__}: {len(rows)} in sqlite, {created} created, {Model.objects.count()} total in pg")
    except Exception as e:
        print(f"{Model.__name__}: ERROR {e}")

try:
    c.execute("SELECT * FROM products_dokumentator")
    rows = c.fetchall()
    for r in rows:
        Dokumentator.objects.get_or_create(id=r['id'], defaults={'name': r['name']})
    print(f"Dokumentator: {len(rows)} in sqlite, {Dokumentator.objects.count()} in pg")
except Exception as e:
    print(f"Dokumentator: {e}")

c.execute("SELECT * FROM products_documentationrequest")
cols = [d[0] for d in c.description]
rows = c.fetchall()
print(f"DocRequest cols: {cols}")
print(f"DocRequest rows in sqlite: {len(rows)}")
created_dr = 0
for r in rows:
    if not DocumentationRequest.objects.filter(id=r['id']).exists():
        dr = DocumentationRequest()
        dr.id = r['id']
        dr.submitted_by_id = r['submitted_by_id']
        dr.tanggal = r['tanggal']
        dr.note = r['note']
        dr.pic_pemohon = r['pic_pemohon']
        dr.status = r['status'] if 'status' in cols else 'TODO'
        if 'brand_materi_id' in cols:
            dr.brand_materi_id = r['brand_materi_id']
        if 'lokasi_id' in cols:
            dr.lokasi_id = r['lokasi_id']
        if 'jenis_led_id' in cols:
            dr.jenis_led_id = r['jenis_led_id']
        dr.save()
        created_dr += 1
print(f"DocRequest: created {created_dr}, total in pg: {DocumentationRequest.objects.count()}")

for table, field in [('products_documentationrequest_requirements','requirements'), ('products_documentationrequest_view_photo','view_photo'), ('products_documentationrequest_jenis_kamera','jenis_kamera')]:
    try:
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()
        cn = [d[0] for d in c.description]
        for r in rows:
            try:
                dr = DocumentationRequest.objects.get(id=r[cn[1]])
                getattr(dr, field).add(r[cn[2]])
            except Exception:
                pass
        print(f"M2M {field}: {len(rows)}")
    except Exception as e:
        print(f"M2M {field}: {e}")

from django.db import connection as pgc
with pgc.cursor() as cur:
    for t in ['products_brandmateri','products_lokasi','products_dokumentator','products_ledtype','products_requirement','products_viewphoto','products_cameratype','products_documentationrequest']:
        try:
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}','id'), COALESCE(MAX(id),1)) FROM {t}")
        except Exception:
            pass
print("SEQUENCES RESET. ALL DONE!")
conn.close()
