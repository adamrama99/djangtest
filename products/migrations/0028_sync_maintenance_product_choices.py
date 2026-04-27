from django.db import migrations


def sync_maintenance_product_choices(apps, schema_editor):
    LEDType = apps.get_model("products", "LEDType")
    NamaPerangkat = apps.get_model("products", "NamaPerangkat")

    existing_names = {
        (name or "").strip().casefold()
        for name in NamaPerangkat.objects.values_list("name", flat=True)
        if name
    }
    missing_products = []

    for product_name in LEDType.objects.order_by("name").values_list("name", flat=True):
        normalized_name = (product_name or "").strip()
        if not normalized_name:
            continue
        casefold_name = normalized_name.casefold()
        if casefold_name in existing_names:
            continue
        existing_names.add(casefold_name)
        missing_products.append(NamaPerangkat(name=normalized_name))

    if missing_products:
        NamaPerangkat.objects.bulk_create(missing_products)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0027_remove_maintenancerequest_jenis_led_and_more"),
    ]

    operations = [
        migrations.RunPython(
            sync_maintenance_product_choices,
            migrations.RunPython.noop,
        ),
    ]
