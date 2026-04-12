from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("legal_documents", "0002_legaldocument_digital_registry_number"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="legaldocument",
            new_name="legal_docum_documen_0f4e05_idx",
            old_name="legal_docum_documen_11d533_idx",
        ),
        migrations.RenameIndex(
            model_name="legaldocument",
            new_name="legal_docum_digital_40739c_idx",
            old_name="legal_docum_digital_be1df4_idx",
        ),
    ]
