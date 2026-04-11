from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("legal_documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="legaldocument",
            name="digital_registry_number",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddIndex(
            model_name="legaldocument",
            index=models.Index(fields=["document_type"], name="legal_docum_documen_11d533_idx"),
        ),
        migrations.AddIndex(
            model_name="legaldocument",
            index=models.Index(
                fields=["digital_registry_number"],
                name="legal_docum_digital_be1df4_idx",
            ),
        ),
    ]
