from django.db import migrations, models


def migrate_maintenance_products_to_led_types(apps, schema_editor):
    LEDType = apps.get_model("products", "LEDType")
    NamaPerangkat = apps.get_model("products", "NamaPerangkat")
    MaintenanceRequest = apps.get_model("products", "MaintenanceRequest")

    led_type_map = {}
    for led_type in LEDType.objects.all().order_by("name"):
        normalized_name = (led_type.name or "").strip().casefold()
        if normalized_name and normalized_name not in led_type_map:
            led_type_map[normalized_name] = led_type.pk

    for nama_perangkat in NamaPerangkat.objects.all().order_by("name"):
        normalized_name = (nama_perangkat.name or "").strip()
        if not normalized_name:
            continue
        casefold_name = normalized_name.casefold()
        if casefold_name in led_type_map:
            continue
        led_type = LEDType.objects.create(name=normalized_name)
        led_type_map[casefold_name] = led_type.pk

    for maintenance_request in MaintenanceRequest.objects.all():
        target_led_ids = []
        for nama_perangkat in maintenance_request.nama_perangkat.all():
            normalized_name = (nama_perangkat.name or "").strip().casefold()
            led_type_id = led_type_map.get(normalized_name)
            if led_type_id:
                target_led_ids.append(led_type_id)
        if target_led_ids:
            maintenance_request.jenis_led.add(*target_led_ids)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0028_sync_maintenance_product_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancerequest",
            name="jenis_led",
            field=models.ManyToManyField(to="products.ledtype", verbose_name="Jenis Produk"),
        ),
        migrations.RunPython(
            migrate_maintenance_products_to_led_types,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="maintenancerequest",
            name="nama_perangkat",
        ),
        migrations.DeleteModel(
            name="NamaPerangkat",
        ),
    ]
