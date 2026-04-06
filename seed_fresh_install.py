import argparse
import os
import sys
import django
import re


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
    # --- AKUN DEFAULT (password plain text) ---
    ('admin@ming.com', 'password', 'Super', 'Admin', ''),
    ('executor@ming.com', 'password', 'Default', 'Executor', 'IT'),
    ('requester@ming.com', 'password', 'Default', 'Requester', 'Marketing'),

    # --- DATA DARI DATABASE LARAVEL (hash bcrypt asli) ---
    # CEO / CREATIVE / DIREKTUR
    ('sandrady.irwan@ming.com', '$2y$12$U/zrj3F/EYP4reKqKWoe8eFq/bTShArpwVFFv7mPoeOamGFu.0l1C', 'Sandrady', 'Irwan', 'CEO'),
    ('thaariq.ibnu@ming.com', '$2y$12$nOwQ3wx89v30OemeSXqN9uvUv7WnoSiuh.vmlCF1y09L02RmeJxHS', 'Thaariq', 'Ibnu', 'CREATIVE'),
    ('ali.salim@ming.com', '$2y$12$HfzNahE66AA2OvHYBx7rMuX32p2n03t229JG9PhIViGWEwCTW2k/2', 'Ali', 'Salim', 'DIREKTUR'),

    # FINANCE
    ('abimanyu.giri@ming.com', '$2y$12$xqK5VZHSQBu2RVKNON1QueAbwhj71alYXuYbVc3nBUE.irxDsHhp6', 'Abimanyu', 'Giri', 'FINANCE'),
    ('butet.siregar@ming.com', '$2y$12$CFkmxngNWCJTtQuZ6q/NsuQ6N5bHYcLs/5RUX7atxS276o2QASjvO', 'Butet', 'Siregar', 'FINANCE'),
    ('deswendri.arung@ming.com', '$2y$12$O./u22RQ1FKhUkx6RiV88utPQVvTbiD13kS7rjagVfzVmBUApNaAC', 'Deswendri', 'Arung', 'FINANCE'),
    ('eka.dewi@ming.com', '$2y$12$Dv1e1uKsps7AipQDL.ahBeKGTSxSWgmCrRuTUL82n.wxhpWoW3GMa', 'Eka', 'Dewi', 'FINANCE'),
    ('fikri.hidayat@ming.com', '$2y$12$7Xt1uKjyxr25x42KW3/i1uAegFDKEGn0ehrs5yq.HFsugeRmqQy3y', 'Fikri', 'Hidayat', 'FINANCE'),
    ('nisrina.rahma@ming.com', '$2y$12$s8xMZaFLk1dY39fLI7EtiumXwT0zfptgA2/xhcHXbq8Bd4qRufhR2', 'Nisrina', 'Rahma', 'FINANCE'),
    ('putri.wahyu@ming.com', '$2y$12$f7SLziJLzhBwwMWrDm6sROXnBxLyB96dSJXeEZGejwBPt30KOf.CK', 'Putri', 'Wahyu', 'FINANCE'),

    # Graphic Design
    ('abie.yudha@ming.com', '$2y$12$MnKlq0MWrxJfQBQf6YjPcehgFWQBxYqg/oCIQmjMB/61yf7rDWCqS', 'Abie', 'Yudha', 'Graphic Design'),
    ('david.christianto@ming.com', '$2y$12$1Wv2r4t3/LG3yPUcZ3vllOzvH0e6SES5EGD7Pt7b2NtSgWXaSRDYu', 'David', 'Christianto', 'Graphic Design'),
    ('fikri.ardiansyah@ming.com', '$2y$12$aRq1Fg3anhhYzU3l3xtq..EJJ/nbU7BwotOIk4M5PkUQeIAujk6IS', 'Fikri', 'Ardiansyah', 'Graphic Design'),
    ('hendro.purwoto@ming.com', '$2y$12$FjLCfpi4tAQ/ACbM43CAjuGvvFGRaYJPmxgOS4ZcvF0PMx3tEaiQO', 'Hendro', 'Purwoto', 'Graphic Design'),
    ('jan.tamado@ming.com', '$2y$12$dCZx2wuaJtOnIegw6dG5auz8TSnqv9vn.iu3aw/GofSZK/6JhEmSe', 'Jan', 'Tamado', 'Graphic Design'),

    # HRD-GA
    ('risda.rochaeti@ming.com', '$2y$12$SJTCn5MhDlJI3qZyfL2rFOxL5XqiFAVXw5FoY/DW3dw9O31KO.v/y', 'Risda', 'Rochaeti', 'HRD-GA'),
    ('ardiansyah@ming.com', '$2y$12$/zzHVvh4Z7dmC1m8oPf4lODZUZw3u8CoH7NNUdTtA4FnG3nYalxq.', 'Ardiansyah', '', 'HRD-GA'),
    ('dedi@ming.com', '$2y$12$.11qqs4xt8uF5msyJV8Jh.46BkNaVzOdPBdudjNY9T5/finIm4DMK', 'Dedi', '', 'HRD-GA'),
    ('rosa@ming.com', '$2y$12$Io5fCIen.Zps0PpHonuWseibSwo4fmL418LQ1KjzbaEOIl74imZBu', 'Rosa', '', 'HRD-GA'),
    ('dian.melva@ming.com', '$2y$12$J6AfizHHH6YunZvJxeU9EeYpg4MrSa51T.QqW2rYeiobjiUSOP65W', 'Dian', 'Melva', 'HRD-GA'),
    ('idawati.tinambunan@ming.com', '$2y$12$3oxue4haUo.FmOXDMg/3H..4yA6b4eJ0xwol3zzMbJINUba8qWh1q', 'Idawati', 'Tinambunan', 'HRD-GA'),
    ('m.tohir@ming.com', '$2y$12$jOv56bf.4S3bz.eLTwu89uWAlf7/qE2R9spxM/m6ISKAE1S40tRZK', 'M.', 'Tohir', 'HRD-GA'),
    ('rehan@ming.com', '$2y$12$Pn1EuuHz/b2WWB5IxjXTtOt5PpOhyrx39FONnl.xhFRFZbGLb6FsK', 'Rehan', '', 'HRD-GA'),
    ('sabraamalisi.dadang@ming.com', '$2y$12$GEmPpibp9PxxoKEPvu0dW.QitxDpLChuVNirISmqn0KLh5cAXjm7G', 'Sabraamalisi', 'Dadang', 'HRD-GA'),
    ('hr@ming.com', '$2y$12$Fx3BkAdFU3LTlZytP2rDaOTpgmZH6u.rC6AdxepjmI4dB0ma9qgju', 'HR', '', 'HRD-GA'),

    # IT
    ('adam.ramadhan@ming.com', '$2y$12$NCHiDBzydjQ.1MDzF2wBaOV6CLcRrfjqt7ob4lF.xbIRBa9QRoBBK', 'Adam', 'Ramadhan', 'IT'),
    ('isnaeni.hidayat@ming.com', '$2y$12$y7XyTfZdcuTgsLdnuGLrseGzH4S9LCWaxrZFa7xsT8CoMUpYjgQpe', 'Isnaeni', 'Hidayat', 'IT'),
    ('rubiyanto@ming.com', '$2y$12$d9jMqwVTbMzcoX25zq9axeQXYWtU75RvK.IzvhhZd.ZYIytFjd6Tm', 'Rubiyanto', '', 'IT'),
    ('aser.suherman@ming.com', '$2y$12$cflV9OAsyfDygM.yNJGCC.oaTqpaIEItLQ530wz.n6kprALLCVY/y', 'Aser', 'Suherman', 'IT'),
    ('fahmi.dwi@ming.com', '$2y$12$V8dg60ho5J3ye98jble6jOU4/kuTgnGnfHTSqqmhx8q90F9VcSitK', 'Fahmi', 'Dwi', 'IT'),
    ('ferri.sihombing@ming.com', '$2y$12$LFBnKxckaz17r7cvqISkSe36Mye1Goihbelo/RUkk/Oi6EaTZdPW6', 'Ferri', 'Sihombing', 'IT'),
    ('handri@ming.com', '$2y$12$bubMFVd22yMuWO.x.FwBXeYAHXDFIYxKH.XJ2dVSGTuMCU.XhuD/u', 'Handri', '', 'IT'),
    ('mujini@ming.com', '$2y$12$O5/JhDiB8n2hj1k7wX.bgeGsdV1LjprbATv9n7D8lKf585OBCLGHS', 'Mujini', '', 'IT'),
    ('surachman@ming.com', '$2y$12$7aRomyNHgij5QQiyOEft4.XW3M.cQeChzCTnf8xIGGIBXeAAH.CSa', 'Surachman', '', 'IT'),
    ('manager@ming.com', '$2y$12$.ouMNMbFUHLsBE/k6mvQAuYhGnxSLK04fPXWBAf9OGtcvm7J6ZHDW', 'Manager', '', 'IT'),

    # Luminova
    ('christian.victor@ming.com', '$2y$12$lzBWlYq.dlxSRlyb0bzSb.a6UAy/TO2IcOPLo8hr9nzQbSBY9si1C', 'Christian', 'Victor', 'Luminova'),
    ('ernest@ming.com', '$2y$12$Exey5wGlquOamhgZCUZVLeyG2vnvpEVupT5YOf4Gx8OlE.WYZuQWC', 'Ernest', '', 'Luminova'),
    ('juan.jonatan@ming.com', '$2y$12$Un9g.5GJVc7ewFdJFbVph.qJx2b5TgeLqMEM7NpTLvSFfQNcW.eeW', 'Juan', 'Jonatan', 'Luminova'),
    ('sandra.marcella@ming.com', '$2y$12$cLAGJMqQImyCmzVd1JuqoeaJMcX88/oiYxKagfe5498kMnJZynadq', 'Sandra', 'Marcella', 'Luminova'),

    # MARKETING
    ('hafidz@ming.com', '$2y$12$xdFa.xhZVwaDKCEfoRVfhu0pzuvH9G5jyjRZEyrQHBeCDhquWMrh2', 'Hafidz', 'Alfian', 'MARKETING'),
    ('ilyas.mutawakkil@ming.com', '$2y$12$05RXR3anMctGhNTqPHD.UOJGoB726aAgxzfJ5OX51c2m9lU0M1yeK', 'Ilyas', 'Mutawakkil', 'MARKETING'),
    ('mawarni.dwi@ming.com', '$2y$12$pb./LqG1s9Nik/pPfZckDuv/fz6CwVVXTenN/HQTdBPVLWn4eQE0S', 'Mawarni', 'Dwi', 'MARKETING'),
    ('tia.pratiwi@ming.com', '$2y$12$dPgWe.pPWFK74PGFi9Y9R.TAAWQ4cAQ3zX7pAqyOedJPaGijeZ5FK', 'Tia', 'Pratiwi', 'MARKETING'),
    ('william.aldoson@ming.com', '$2y$12$GtksDzBquCx4T1zdEUAUSuIQG.SV7x.FjCDgIGcI7MD0VP6csQR7C', 'William', 'Aldoson', 'MARKETING'),
    ('ahmad.lutfi@ming.com', '$2y$12$jSM7CkHVK.f5imgmPAxKKOR6jMTC1Fy39p1eB1r.6qzSfcLUQF672', 'Ahmad', 'Lutfi', 'MARKETING'),
    ('erik.setiawan@ming.com', '$2y$12$ShuF0dmRYcEBeUI4NXSX.efAigfGSDRjV4pNUQQxTAkI2gYKcy/6a', 'Erik', 'Setiawan', 'MARKETING'),

    # Product Development
    ('supriyanto@ming.com', '$2y$12$qogetIWzvhd8mBKhiVoBU.EPs5y6H/shzOorafCsnrAyXnp0SIGni', 'Supriyanto', '', 'Product Development'),
    ('andaru.baskara@ming.com', '$2y$12$oKOqluKRzxxc8TOw3MXgi.JaoSfk1ZYy5AX9tzq0T4jeGhQik6gs6', 'Andaru', 'Baskara', 'Product Development'),
    ('dame.ayu@ming.com', '$2y$12$5nGgPOoHbRJajpwR9ZQu4.U2nCkpHCeOEE9gZr.jLCpwVY4m3QbHq', 'Dame', 'Ayu', 'Product Development'),
    ('dimas.wahyu@ming.com', '$2y$12$8usQ7VGw6TQTi/BfCtNn6O5yBX44KoBu5ynjsu0mDrr2o9ou6CBEm', 'Dimas', 'Wahyu Tinular', 'Product Development'),
    ('fahri@ming.com', '$2y$12$F/JVyPr1QlU8gX1ybzDaue7DBm8ftwnMYyKNqFHh3s3jbzy9EWZIO', 'Fahri', '', 'Product Development'),
    ('nanda@ming.com', '$2y$12$7Fgl2Lr4jEwFLFHJUVzZ/eIfp91DsYRRNPHq.Z5fsfRhYhiLd987y', 'Nanda', '', 'Product Development'),

    # Mobile LED
    ('nurun.nisah@ming.com', '$2y$12$yyRDWl7ooc6f7GgHSDEAa.4gB1vdkYxxsmZJZxUtmg0p5GfAMrJNi', 'Nurun', 'Nisah', 'Mobile LED'),
    ('aura.chitra@ming.com', '$2y$12$SaN7vl2UzVb9rjkBb7dI0e6kpHuzs9e/4RzLG1j2WonFHySE69Ki.', 'Aura', 'Chitra', 'Mobile LED'),

    # PRODUKSI
    ('budi.kameswaraopus@ming.com', '$2y$12$5apY2QBpBNxgeOdFWphJhep7rZt3AfHHX3LFg1CSGRSK8GNsS8i3a', 'Budi', 'Kameswara(Opus)', 'PRODUKSI'),
    ('masuri@ming.com', '$2y$12$wEi3F4qewRBOOZ4bm1yhy.9Fci2vvHoPOBv2rFNCoFFFWuOS.raZO', 'Masuri', '', 'PRODUKSI'),
    ('mefi.defiyana@ming.com', '$2y$12$XUJyGazvhsUKD5267jynFO8TFABttRkwQgsFvzG1jblfyRNT16qgG', 'Mefi', 'Defiyana', 'PRODUKSI'),
    ('moch.hafri@ming.com', '$2y$12$F7oqJkfkCHJWFIxK4bmKJePEDaM7M1CKvswnbvwpTn0giX0Fq.nOC', 'Moch.', 'Hafri', 'PRODUKSI'),
    ('mochammad.ichwan@ming.com', '$2y$12$7yjPFBTefL6hjzHDMxCepu0Hk8ph.veL4m6rw93SnEZiWqKu5sMIm', 'Mochammad', 'Ichwan', 'PRODUKSI'),
    ('muhammad.dali@ming.com', '$2y$12$IcODnDNsZpomMx2WV4DSXO07YDEDXwti7fw5M1ZJLv/uAEDAlW23S', 'Muhammad', 'Dali', 'PRODUKSI'),
    ('sharen.wibowo@ming.com', '$2y$12$ZATIM2N9mNZGVtJ6fuaLLubDp1rDZCF0NbnrusDFTIVd/s/AMZUFK', 'Sharen', 'Wibowo', 'PRODUKSI'),
    ('sunyarno@ming.com', '$2y$12$jRMQgIhmowMP8DijqMlzSO.f1e0khapRxD.CMf4vVFr2RxfdybXPG', 'Sunyarno', '', 'PRODUKSI'),
    ('ahmad.samhudi@ming.com', '$2y$12$0BYeVhkd5efYp7zSqTiDju0JAU.uTIp7fDtRwRAK.LpIcUAS4amAy', 'Ahmad', 'Samhudi', 'PRODUKSI'),
    ('ajimadi.jaya@ming.com', '$2y$12$adWVJ2hBCiuaFJVciAON2epixLgetRv0gLxO0dSCY.PdxheRk6x62', 'Ajimadi', 'Jaya', 'PRODUKSI'),
    ('amirudin@ming.com', '$2y$12$eCIoNWpeA.pE5K9kJF2n8O70idD8XtEul1f3lNjLHNiIGgkqsF0O2', 'Amirudin', '', 'PRODUKSI'),
    ('angga.pratomo@ming.com', '$2y$12$R.NQLKSNeZ8wMXzN16jlheaIUd86R0iNOu/9UEo7J3sB2AV8KCxsO', 'Angga', 'Pratomo', 'PRODUKSI'),
    ('aris.suyitno@ming.com', '$2y$12$h6gdacDcyhzl3aPU2VTBv.unFudvJwLYVYN011KLPhFJTj1ZphrgO', 'Aris', 'Suyitno', 'PRODUKSI'),
    ('gilang.ramadhan@ming.com', '$2y$12$6J4AGf3qwqUyfX8eTVxDs.JxUYXSAymYQT.JA6XcLOZGPzuKNoipW', 'Gilang', 'Ramadhan', 'PRODUKSI'),
    ('karta@ming.com', '$2y$12$kqlyaQLCH08vYw7VgONt1ezQUQVEyPPJWYIC6MwFFkf8b7ldyb3I2', 'Karta', '', 'PRODUKSI'),
    ('mohamad.nur@ming.com', '$2y$12$TPD4SkUBKhChxKI7ep8pu.8KFmS68FFckO/tHKL403IM7DGZ0rRSC', 'Mohamad', 'Nur', 'PRODUKSI'),
    ('rahmat@ming.com', '$2y$12$g6drcmXO/QiG//21lJRIreQXM4aiWls1n3l39jOa1Uckbmx18qxoO', 'Rahmat', '', 'PRODUKSI'),
    ('sapri@ming.com', '$2y$12$l7cNij4yeXgW9IgHn05pRu5neJOavPjG1RYPUCbGKRmx4x.dANdJm', 'Sapri', '', 'PRODUKSI'),
    ('supadi@ming.com', '$2y$12$mUnjk9u2gfKH/j0TbpELR.iNiuVJ0IT/f6ounIXh.o3oysSioY2XC', 'Supadi', '', 'PRODUKSI'),
    ('supono@ming.com', '$2y$12$tSvXFnOyjv0hs/zGtoFyCevyGN0MC/VPGsjsbR66XJfKza0sFjbjy', 'Supono', '', 'PRODUKSI'),
    ('yuli.guntoro@ming.com', '$2y$12$uFXNiDY4LKnEjOQ.q2YVjePHTKbUYUZZYh8RN8nkgaAHnoX6uwgSK', 'Yuli', 'Guntoro', 'PRODUKSI'),

    # SALES
    ('angela.rahardy@ming.com', '$2y$12$55OHtXcNfL8etgkx9RUbz.AVid9Cp1F5LTHVCJEKl1cDy9zoG/QX6', 'Angela', 'Rahardy', 'SALES'),
    ('damayanti@ming.com', '$2y$12$QzeQxY8Zd2yMsw9cBB5qVu3/Q3ze5uY4e8qdRXdTE/vX1d6Rg3QYq', 'Damayanti', '', 'SALES'),
    ('della.kusuma@ming.com', '$2y$12$9oMhsAEC7kGPpCB8Vbs4huNlqwwFvEBSMyp4IJraA1YpRoiYarCzW', 'Della', 'Kusuma', 'SALES'),
    ('hafifah.irliani@ming.com', '$2y$12$72igu0IJ7vgE1Dmp5mm7Q.Mbw.vf9qSFPPfoNAB5K4/M5b.qSxnom', 'Hafifah', 'Irliani', 'SALES'),
    ('hani.hara@ming.com', '$2y$12$OloqgCgQqr88BJD6IqrxsOqwHQuPp6umQyZVR8CWNBdDEbu5/GnBK', 'Hani', 'Hara', 'SALES'),
    ('imam.budyarso@ming.com', '$2y$12$voIMNk3cqPVVBrZnBqjlnObnc4btBbipZMCC7vCfhhW4h7gXat5vG', 'Imam', 'Budyarso', 'SALES'),
    ('imelda.febriana@ming.com', '$2y$12$rg6RMZWMp/P1AtSlDnoI.OBr/nEseaaJJaNp6xsUI3IT8nazT9Eau', 'Imelda', 'Febriana', 'SALES'),
    ('indra.winata@ming.com', '$2y$12$baUaRKGrywEVie4YFsUKaexb8CkM1TbrH3lS1Ym3Zh5dcPjvdWkUG', 'Indra', 'Winata', 'SALES'),
    ('marliyani.khou@ming.com', '$2y$12$EWvAcsst6f8fpByg7CSyoeMcvM2XS1YmjIZgmLIhDd9ojVeeG04ae', 'Marliyani', 'Khou', 'SALES'),
    ('reza.bagoes@ming.com', '$2y$12$ryclHt8xICTejBrq5QdW5OHIh/noeK6uWaTn453c76gii2G81PG6G', 'Reza', 'Bagoes', 'SALES'),
    ('rubby.larasati@ming.com', '$2y$12$F8eDRGba.WCXGPGz/3eGcuWuRqkbEzvmbkK4vZUsXdRN5cDwrxAMm', 'Rubby', 'Larasati', 'SALES'),
    ('vara.febriyanti@ming.com', '$2y$12$8tO5aon/q7Q/CTVuYoXODu2w5WKaxGoqyqP9jkBeCxb/6MKvtDMcu', 'Vara', 'Febriyanti', 'SALES'),
    ('wimpy.novanda@ming.com', '$2y$12$dCtXah46nydYyAU57UmgU.gs92Pa.kDDYkc8iUUndElqXf5tQTrBi', 'Wimpy', 'Novanda', 'SALES'),
    ('yulia.andani@ming.com', '$2y$12$dh8vIdyxPcS3brnG5U1ibubcjr8NFie2ZeSgjMSaDmERMiFiUA7Eq', 'Yulia', 'Andani', 'SALES'),
    ('yuniawati@ming.com', '$2y$12$ps/ZFxR/c7GOQ.N2o8ZPdONY95dqdeHeehrtjYl/ZYDhbdSatwiYW', 'Yuniawati', '', 'SALES'),

    # Admin original
    ('ming@ming.com', '$2y$12$uXKSqP2EqUsjNdjRLJDS3.v8.SY050pw252GA1roBGNfLinAg2Wxu', 'Admin', 'Original', ''),
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

def generate_unique_username(base_username):
    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return username

def is_valid_bcrypt(pw):
    """Valid bcrypt hash = exactly 60 chars: $2y$XX$ (7) + salt+hash (53)"""
    return pw.startswith('$2y$') and len(pw) == 60


def create_user(email, password, first_name, last_name, divisi):
    if User.objects.filter(email__iexact=email).exists():
        return None

    base_username = email.split('@')[0]
    username = generate_unique_username(base_username)

    if divisi == "IT":
        role = "executor"
    elif divisi == "":
        role = "admin"
    else:
        role = "requester"

    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name
    )

    if is_valid_bcrypt(password):
        user.password = 'bcrypt$' + password.replace('$2y$', '$2b$')
    elif password.startswith('pbkdf2_') or password.startswith('bcrypt$'):
        user.password = password
    else:
        user.set_password("password123")

    # ✅ WAJIB DI LUAR
    user.save()

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
