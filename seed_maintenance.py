"""
Seed script for Maintenance & Troubleshoot LED master data.
Run: python seed_maintenance.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from products.models import LEDType, InventoryItem

# Jenis Produk
jenis_produk_list = ['Mobile LED', 'LED Statis', 'Outdoor LED', 'Billboard', 'Banner', 'Videotrone', 'Neon Box']
for name in jenis_produk_list:
    obj, created = LEDType.objects.get_or_create(name=name)
    print(f"  {'Created' if created else 'Exists'}: LEDType '{name}'")

# Inventory Items by group
inventory_data = {
    'MING': [
        'Kuningan City', 'Gandaria City', 'PIM 1', 'PIM 2',
        'Metropolitan Mall', 'Kemang', 'Ukrida', 'Kota Kasablanka',
        'Lotte Mall', 'Paskal', 'Kualanamu', 'Beos',
        'Ambasador', 'Bsd Eksklusif', 'Wtc Serpong', 'Bsd Junction 2',
    ],
    'MOBILE_LED': ['Mobile LED'],
    'MST': ['Mbloc', 'Cibis'],
    'LUMINOVA': ['LED Rental', 'Mobile LED Transformer', 'Mobile LED Stage'],
}

for group, items in inventory_data.items():
    for name in items:
        obj, created = InventoryItem.objects.get_or_create(name=name, group=group)
        print(f"  {'Created' if created else 'Exists'}: InventoryItem '{name}' ({group})")

print("\nDone!")
