from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.legal_documents.models import LegalDocument
from apps.legal_indexing.services.ingestion import parse_document_into_fragments
from apps.legal_sources.models import Source


SEED_SOURCES = [
    {
        "name": "Ley Federal del Trabajo",
        "slug": "lft",
        "type": Source.SourceType.LAW,
        "authority": "Camara de Diputados",
        "official_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
        "description": "Texto vigente de la Ley Federal del Trabajo.",
    },
    {
        "name": "Ley del Seguro Social",
        "slug": "lss",
        "type": Source.SourceType.LAW,
        "authority": "Camara de Diputados",
        "official_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf",
        "description": "Texto vigente de la Ley del Seguro Social.",
    },
    {
        "name": "Semanario Judicial de la Federacion",
        "slug": "sjf",
        "type": Source.SourceType.JURISPRUDENCE,
        "authority": "SCJN",
        "official_url": "https://sjf2.scjn.gob.mx/busqueda-principal-tesis",
        "description": "Tesis y precedentes relevantes.",
    },
    {
        "name": "Diario Oficial de la Federacion",
        "slug": "dof",
        "type": Source.SourceType.GAZETTE,
        "authority": "DOF",
        "official_url": "https://www.dof.gob.mx/",
        "description": "Validacion de publicaciones y reformas.",
    },
]


SEED_DOCUMENTS = [
    {
        "source_slug": "lft",
        "title": "Ley Federal del Trabajo",
        "short_name": "LFT",
        "document_type": LegalDocument.DocumentType.LAW,
        "subject_area": LegalDocument.SubjectArea.LABOR,
        "publication_date": date(1970, 4, 1),
        "effective_date": date(1970, 5, 1),
        "last_reform_date": date(2026, 1, 15),
        "version_label": "vigente-2026-01-15",
        "raw_text": """
Articulo 47. Son causas de rescision de la relacion de trabajo, sin responsabilidad para el patron, las faltas de probidad u honradez, actos de violencia, amenazas, injurias o malos tratamientos del trabajador.

Articulo 51. Son causas de rescision de la relacion de trabajo, sin responsabilidad para el trabajador, enganarlo el patron, reducir el salario o comprometer la seguridad o salud del trabajador.

Articulo 473. Riesgos de trabajo son los accidentes y enfermedades a que estan expuestos los trabajadores en ejercicio o con motivo del trabajo.

Articulo 474. Accidente de trabajo es toda lesion organica o perturbacion funcional, inmediata o posterior, producida repentinamente en ejercicio o con motivo del trabajo.

Articulo 487. Los trabajadores que sufran un riesgo de trabajo tendran derecho a asistencia medica, rehabilitacion, hospitalizacion, medicamentos e indemnizacion correspondiente.
""".strip(),
    },
    {
        "source_slug": "lss",
        "title": "Ley del Seguro Social",
        "short_name": "LSS",
        "document_type": LegalDocument.DocumentType.LAW,
        "subject_area": LegalDocument.SubjectArea.SOCIAL_SECURITY,
        "publication_date": date(1995, 12, 21),
        "effective_date": date(1997, 7, 1),
        "last_reform_date": date(2026, 1, 15),
        "version_label": "vigente-2026-01-15",
        "raw_text": """
Articulo 41. Riesgos de trabajo son los accidentes y enfermedades a que estan expuestos los trabajadores en ejercicio o con motivo del trabajo.

Articulo 42. Se considera accidente de trabajo toda lesion organica o perturbacion funcional producida repentinamente en ejercicio o con motivo del trabajo.

Articulo 43. En caso de accidente de trabajo el patron debe dar aviso al Instituto en los terminos reglamentarios.

Articulo 58. El asegurado que sufra un riesgo de trabajo tiene derecho a las prestaciones en especie y en dinero que correspondan conforme a esta Ley.
""".strip(),
    },
    {
        "source_slug": "sjf",
        "title": "Tesis sobre renuncia y riesgo de trabajo",
        "short_name": "SJF",
        "document_type": LegalDocument.DocumentType.THESIS,
        "subject_area": LegalDocument.SubjectArea.GENERAL,
        "publication_date": date(2024, 9, 1),
        "effective_date": date(2024, 9, 1),
        "last_reform_date": date(2024, 9, 1),
        "version_label": "tesis-demo-v1",
        "digital_registry_number": "2026001",
        "raw_text": """
Rubro. Renuncia firmada bajo presion. Cuando una persona trabajadora afirma que la renuncia fue obtenida bajo presion o despues de un accidente de trabajo, el juzgador debe analizar integralmente el contexto probatorio.

Tesis. Riesgo de trabajo y proteccion reforzada. La incapacidad emitida por institucion de seguridad social y la continuidad del tratamiento medico son indicios relevantes para valorar la situacion laboral de la persona trabajadora.
""".strip(),
    },
]


DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "Admin12345!",
        "role": "admin",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "researcher",
        "email": "researcher@example.com",
        "password": "Research12345!",
        "role": "researcher",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "username": "demo",
        "email": "demo@example.com",
        "password": "Demo12345!",
        "role": "user",
        "is_staff": False,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = "Seeds demo users, legal sources and sample legal documents."

    def handle(self, *args, **options):
        self.seed_users()
        sources = self.seed_sources()
        self.seed_documents(sources)
        self.stdout.write(self.style.SUCCESS("Seed data ready."))

    def seed_users(self):
        user_model = get_user_model()
        for item in DEMO_USERS:
            user, created = user_model.objects.get_or_create(
                username=item["username"],
                defaults={
                    "email": item["email"],
                    "role": item["role"],
                    "is_staff": item["is_staff"],
                    "is_superuser": item["is_superuser"],
                },
            )
            changed = False
            for field in ("email", "role", "is_staff", "is_superuser"):
                if getattr(user, field) != item[field]:
                    setattr(user, field, item[field])
                    changed = True
            if created or not user.check_password(item["password"]):
                user.set_password(item["password"])
                changed = True
            if changed:
                user.save()
            self.stdout.write(f"User ready: {user.username}")

    def seed_sources(self):
        created_sources = {}
        for item in SEED_SOURCES:
            source, _ = Source.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "type": item["type"],
                    "authority": item["authority"],
                    "official_url": item["official_url"],
                    "description": item["description"],
                    "is_active": True,
                },
            )
            created_sources[item["slug"]] = source
            self.stdout.write(f"Source ready: {source.name}")
        return created_sources

    def seed_documents(self, sources):
        for item in SEED_DOCUMENTS:
            source = sources[item["source_slug"]]
            document, _ = LegalDocument.objects.update_or_create(
                source=source,
                title=item["title"],
                version_label=item["version_label"],
                defaults={
                    "short_name": item["short_name"],
                    "document_type": item["document_type"],
                    "subject_area": item["subject_area"],
                    "publication_date": item["publication_date"],
                    "effective_date": item["effective_date"],
                    "last_reform_date": item["last_reform_date"],
                    "official_url": source.official_url,
                    "digital_registry_number": item.get("digital_registry_number", ""),
                    "raw_text": item["raw_text"],
                    "metadata_json": {"seeded": True},
                    "is_current": True,
                },
            )
            parse_document_into_fragments(document)
            self.stdout.write(f"Document ready: {document.title}")
