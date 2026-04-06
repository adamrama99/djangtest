import argparse
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth.models import User, Group
from products.models import (
    BrandMateri,
    Lokasi,
    cameratype,
    LEDType,
    Requirement,
    ViewPhoto,
    Dokumentator,
    NamaPerangkat,
    InventoryItem,
    TakeoutAlertRule,
)

OPTION_DATA = {
    'brand_materi': ['Samsung', 'Shoppee', 'samsung'],
    'lokasi': ['Jakpus', 'WTC'],
    'camera_types': ['Iphone', 'Android', 'Kamera DSLR'],
    'led_types': ['Mobile LED', 'LED Statis', 'Outdoor LED', 'Billboard', 'Banner'],
    'requirements': ['HIGHRESS', 'SIANG', 'MALAM', 'TIME STAMP', 'NON TIME STAMP'],
    'view_photos': ['PORTRAIT', 'LANDSCAPE', 'JARAK DEKAT', 'JARAK SEDANG', 'JARAK JAUH'],
    'dokumentators': ['Surachman', 'Asep', 'executor'],
    'nama_perangkat': ['Videotrone', 'Neon Box', 'Billboard'],
}

INVENTORY_ITEMS = {
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

TAKEOUT_ALERT_RULES = [
    {
        'name': 'H-1 Warning',
        'trigger_direction': 'BEFORE',
        'offset_unit': 'DAY',
        'offset_value': 1,
        'urgency': 'WARNING',
        'is_active': True,
    },
    {
        'name': 'Jam-6 takeout',
        'trigger_direction': 'BEFORE',
        'offset_unit': 'HOUR',
        'offset_value': 6,
        'urgency': 'URGENT',
        'is_active': True,
    },
    {
        'name': 'lewat waktu takeout',
        'trigger_direction': 'AFTER',
        'offset_unit': 'HOUR',
        'offset_value': 0,
        'urgency': 'URGENT',
        'is_active': True,
    },
]

GROUP_NAMES = ['admin', 'staff', 'requester', 'executor']


def parse_args():
    parser = argparse.ArgumentParser(description='Seed fresh install data.')
    parser.add_argument('--reset', action='store_true', help='Delete old option and seeded user data before seeding.')
    return parser.parse_args()


def clear_option_data():
    print('Clearing old option data...')
    for model in [
        BrandMateri,
        Lokasi,
        cameratype,
        LEDType,
        Requirement,
        ViewPhoto,
        Dokumentator,
        NamaPerangkat,
        InventoryItem,
        TakeoutAlertRule,
    ]:
        deleted, _ = model.objects.all().delete()
        print(f'  Cleared {deleted} records from {model.__name__}')


def clear_seed_users():
    print('Clearing old seeded users...')
    emails = [email for email, _, _, _, _ in USERS]
    deleted, _ = User.objects.filter(email__in=emails).delete()
    print(f'  Cleared {deleted} user records')

USERS = [
    ('admin@company.com', 'password', 'Super', 'Admin', 'IT'),
    ('executor@company.com', 'password', 'Default', 'Executor', 'IT'),
    ('requester@company.com', 'password', 'Default', 'Requester', 'Marketing'),

    ('sandrady.irwan@ming.com', '$2y$12$U/zrj3F/EYP4reKqKWoe8eFq/bTShArpwVFFv7mPoeOamGFu.0l1C', 'Sandrady', 'Irwan', 'CEO'),
    ('thaariq.ibnu@ming.com', '$2y$12$nOwQ3wx89v30OemeSXqN9uvUv7WnoSiuh.vmlCF1y09L02RmeJxHS', 'Thaariq', 'Ibnu', 'CREATIVE'),
    ('ali.salim@ming.com', '$2y$12$HfzNahE66AA2OvHYBx7rMuX32p2n03t229JG9PhIViGWEwCTW2k/2', 'Ali', 'Salim', 'DIREKTUR'),

    ('abimanyu.giri@ming.com', '$2y$12$F8M2fU8pB08j7QWq3zXvOu1.Y9VzR6Y7N8B9C0D1E2F3G4H5I6J7', 'Abimanyu', 'Giri', 'FINANCE'),
    ('butet.siregar@ming.com', '$2y$12$G9N3gV9qC19k8RXr4aYwPv2.Z0WaS7Z8O9C0D1E2F3G4H5I6J7K8', 'Butet', 'Siregar', 'FINANCE'),
    ('deswendri.arung@ming.com', '$2y$12$H0O4hW0rD20l9SYs5bZxQw3.A1XbT8A9P0D1E2F3G4H5I6J7L9', 'Deswendri', 'Arung', 'FINANCE'),
    ('eka.dewi@ming.com', '$2y$12$I1P5iX1sE31m0TZt6cAyRx4.B2YcU9B0Q1D1E2F3G4H5I6J7M0', 'Eka', 'Dewi', 'FINANCE'),
    ('fikri.hidayat@ming.com', '$2y$12$J2Q6jY2tF42n1Uau7dBzSy5.C3ZdV0C1R1D1E2F3G4H5I6J7N1', 'Fikri', 'Hidayat', 'FINANCE'),
    ('nisrina.rahma@ming.com', '$2y$12$K3R7kZ3uG53o2Vbv8eC0Tz6.D4AeW1D2S1D1E2F3G4H5I6J7O2', 'Nisrina', 'Rahma', 'FINANCE'),
    ('putri.wahyu@ming.com', '$2y$12$L4S8lA4vH64p3Wcw9fD1Ua7.E5BfX2E3T1D1E2F3G4H5I6J7P3', 'Putri', 'Wahyu', 'FINANCE'),

    ('abie.yudha@ming.com', '$2y$12$M5T9mB5wI75q4Xdx0gE2Vb8.F6CgY3F4U1D1E2F3G4H5I6J7Q4', 'Abie', 'Yudha', 'Graphic Design'),
    ('david.christianto@ming.com', '$2y$12$N6U0nC6xJ86r5Yey1hF3Wc9.G7DhZ4G5V1D1E2F3G4H5I6J7R5', 'David', 'Christianto', 'Graphic Design'),
    ('fikri.ardiansyah@ming.com', '$2y$12$O7V1oD7yK97s6JpJ2sQ4Hn0.H8EiA5H6W1D1E2F3G4H5I6J7S6', 'Fikri', 'Ardiansyah', 'Graphic Design'),
    ('hendro.purwoto@ming.com', '$2y$12$P8W2pE8zL08t7AgA3jH5Ye1.I9FjB6I7X1D1E2F3G4H5I6J7T7', 'Hendro', 'Purwoto', 'Graphic Design'),
    ('jan.tamado@ming.com', '$2y$12$Q9X3qF9aM19u8BhB4kI6Zf2.J0GkC7J8Y1D1E2F3G4H5I6J7U8', 'Jan', 'Tamado', 'Graphic Design'),

    ('risda.rochaeti@ming.com', '$2y$12$R0Y4rG0bN20v9CiC5lJ7Ag3.K1HlD8K9Z1D1E2F3G4H5I6J7V9', 'Risda', 'Rochaeti', 'HRD-GA'),
    ('ardiansyah@ming.com', '$2y$12$S1Z5sH1cO31w0DjD6mK8Bh4.L2ImE9L0A1D1E2F3G4H5I6J7W0', 'Ardiansyah', '', 'HRD-GA'),
    ('dedi@ming.com', '$2y$12$T2A6tI2dP42x1EkE7nL9Ci5.M3JnF0M1B1D1E2F3G4H5I6J7X1', 'Dedi', '', 'HRD-GA'),
    ('rosa@ming.com', '$2y$12$U3B7uJ3eQ53y2FlF8oM0Dj6.N4KoG1N2C1D1E2F3G4H5I6J7Y2', 'Rosa', '', 'HRD-GA'),
    ('dian.melva@ming.com', '$2y$12$V4C8vK4fR64z3GmG9pN1Ek7.O5LpH2O3D1D1E2F3G4H5I6J7Z3', 'Dian', 'Melva', 'HRD-GA'),
    ('idawati.tinambunan@ming.com', '$2y$12$W5D9wL5gS75a4HnH0qO2Fl8.P6MqI3P4E1D1E2F3G4H5I6J7A4', 'Idawati', 'Tinambunan', 'HRD-GA'),
    ('m.tohir@ming.com', '$2y$12$X6E0xM6hT86b5IoI1rP3Gm9.Q7NrJ4Q5F1D1E2F3G4H5I6J7B5', 'M.', 'Tohir', 'HRD-GA'),
    ('rehan@ming.com', '$2y$12$Y7F1yN7iU97c6JpJ2sQ4Hn0.R8OsK5R6G1D1E2F3G4H5I6J7C6', 'Rehan', '', 'HRD-GA'),
    ('sabraamalisi.dadang@ming.com', '$2y$12$Z8G2zO8jV08d7KqK3tR5Io1.S9PtL6S7H1D1E2F3G4H5I6J7D7', 'Sabraamalisi', 'Dadang', 'HRD-GA'),

    ('adam.ramadhan@ming.com', '$2y$12$A9H3aP9kW19e8LrL4uS6Jp2.T0QuM7T8I1D1E2F3G4H5I6J7E8', 'Adam', 'Ramadhan', 'IT'),
    ('isnaeni.hidayat@ming.com', '$2y$12$B0I4bQ0lX20f9MsM5vT7Kq3.U1RvN8U9J1D1E2F3G4H5I6J7F9', 'Isnaeni', 'Hidayat', 'IT'),

    ('christian.victor@ming.com', '$2y$12$C1J5cR1mY31g0NtN6wU8Lr4.V2SwO9V0K1D1E2F3G4H5I6J7G0', 'Christian', 'Victor', 'Luminova'),
    ('ernest@ming.com', '$2y$12$D2K6dS2nZ42h1OuO7xV9Ms5.W3TxP0W1L1D1E2F3G4H5I6J7H1', 'Ernest', '', 'Luminova'),
    ('juan.jonatan@ming.com', '$2y$12$E3L7eT3oA53i2PvP8yW0Nt6.X4UyQ1X2M1D1E2F3G4H5I6J7I2', 'Juan', 'Jonatan', 'Luminova'),
    ('sandra.marcella@ming.com', '$2y$12$F4M8fU4pB64j3QwQ9zX1Ou7.Y5VzR2Y3N1D1E2F3G4H5I6J7J3', 'Sandra', 'Marcella', 'Luminova'),

    ('hafidz@ming.com', '$2y$12$v9H7Z0v.zQ6P6j.5W8e7be7be7be7be7be7be7be7be7be7be7be7', 'Hafidz', 'Alfian', 'MARKETING'),
    ('ilyas.mutawakkil@ming.com', '$2y$12$w0I8a1w.aR7Q7k.6X9f8cf8cf8cf8cf8cf8cf8cf8cf8cf8cf8cf', 'Ilyas', 'Mutawakkil', 'MARKETING'),
    ('mawarni.dwi@ming.com', '$2y$12$x1J9b2x.bS8R8l.7Y0g9dg9dg9dg9dg9dg9dg9dg9dg9dg9dg9dg', 'Mawarni', 'Dwi', 'MARKETING'),
    ('tia.pratiwi@ming.com', '$2y$12$y2K0c3y.cT9S9m.8Z1h0eh0eh0eh0eh0eh0eh0eh0eh0eh0eh0eh', 'Tia', 'Pratiwi', 'MARKETING'),
    ('william.aldoson@ming.com', '$2y$12$z3L1d4z.dU0T0n.9A2i1fi1fi1fi1fi1fi1fi1fi1fi1fi1fi1fi', 'William', 'Aldoson', 'MARKETING'),

    ('supriyanto@ming.com', '$2y$12$g6drcmXO/QiG//21lJRIreQXM4aiWls1n3l39jOa1Uckbmx18qxoO', 'Supriyanto', '', 'Product Development'),
    ('nurun.nisah@ming.com', '$2y$12$mUnjk9u2gfKH/j0TbpELR.iNiuVJ0IT/f6ounIXh.o3oysSioY2XC', 'Nurun', 'Nisah', 'Mobile LED'),
    ('rubiyanto@ming.com', '$2y$12$tSvXFnOyjv0hs/zGtoFyCevyGN0MC/VPGsjsbR66XJfKza0sFjbjy', 'Rubiyanto', '', 'IT'),
    ('ahmad.lutfi@ming.com', '$2y$12$7aRomyNHgij5QQiyOEft4.XW3M.cQeChzCTnf8xIGGIBXeAAH.CSa', 'Ahmad', 'Lutfi', 'MARKETING'),
]

def seed_groups():
    print('Seeding groups...')
    for name in GROUP_NAMES:
        group, created = Group.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: Group {name}')


def seed_option_data():
    print('Seeding option data...')

    for name in OPTION_DATA['brand_materi']:
        obj, created = BrandMateri.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: BrandMateri {name}')

    for name in OPTION_DATA['lokasi']:
        obj, created = Lokasi.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: Lokasi {name}')

    for name in OPTION_DATA['camera_types']:
        obj, created = cameratype.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: cameratype {name}')

    for name in OPTION_DATA['led_types']:
        obj, created = LEDType.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: LEDType {name}')

    for name in OPTION_DATA['requirements']:
        obj, created = Requirement.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: Requirement {name}')

    for name in OPTION_DATA['view_photos']:
        obj, created = ViewPhoto.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: ViewPhoto {name}')

    for name in OPTION_DATA['dokumentators']:
        obj, created = Dokumentator.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: Dokumentator {name}')

    for name in OPTION_DATA['nama_perangkat']:
        obj, created = NamaPerangkat.objects.get_or_create(name=name)
        print(f'  {"Created" if created else "Exists"}: NamaPerangkat {name}')

    for group_name, items in INVENTORY_ITEMS.items():
        for item_name in items:
            obj, created = InventoryItem.objects.get_or_create(name=item_name, group=group_name)
            print(f'  {"Created" if created else "Exists"}: InventoryItem {item_name} ({group_name})')

    for rule in TAKEOUT_ALERT_RULES:
        obj, created = TakeoutAlertRule.objects.get_or_create(
            name=rule['name'],
            defaults={
                'trigger_direction': rule['trigger_direction'],
                'offset_unit': rule['offset_unit'],
                'offset_value': rule['offset_value'],
                'urgency': rule['urgency'],
                'is_active': rule['is_active'],
            },
        )
        if not created:
            changed = False
            for field in ['trigger_direction', 'offset_unit', 'offset_value', 'urgency', 'is_active']:
                if getattr(obj, field) != rule[field]:
                    setattr(obj, field, rule[field])
                    changed = True
            if changed:
                obj.save()
        print(f'  {"Created" if created else "Exists"}: TakeoutAlertRule {rule["name"]}')


from django.contrib.auth.hashers import make_password

def normalize_bcrypt(password):
    if password.startswith('$2y$'):
        return password.replace('$2y$', '$2b$', 1)
    return password

def generate_unique_username(base_username):
    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return username

def create_user(email, password, first_name, last_name, divisi):
    if User.objects.filter(email__iexact=email).exists():
        return None

    base_username = email.split('@')[0]
    username = generate_unique_username(base_username)

    # tentukan role
    role = "executor" if divisi == "IT" else "requester"

    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=role.capitalize()  # optional kalau mau ditampilin
    )

    if password.startswith('$2'):
        user.password = normalize_bcrypt(password)
    else:
        user.set_password(password)

    user.save()

    # assign ke group
    group = Group.objects.get(name=role)
    user.groups.add(group)

    return user, role

def seed_users():
    print('Seeding users...')
    created = 0
    skipped = 0

    for email, password, first_name, last_name, divisi in USERS:
        result = create_user(email, password, first_name, last_name, divisi)

        if result is None:
            print(f"  SKIP: {email} already exists")
            skipped += 1
        else:
            user, role = result
            print(f"  CREATED: {email} ({first_name}) - {divisi} -> {role}")
            created += 1

    print(f'Users created: {created}, skipped: {skipped}')


def main():
    args = parse_args()
    if args.reset:
        clear_option_data()
        clear_seed_users()

    seed_groups()
    seed_option_data()
    seed_users()
    print('Fresh install seed complete.')


if __name__ == '__main__':
    main()
