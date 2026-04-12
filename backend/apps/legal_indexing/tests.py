from django.test import SimpleTestCase

from .services.ingestion import _split_document


class IngestionParsingTests(SimpleTestCase):
    def test_split_document_does_not_treat_inline_article_mentions_as_article_headers(self):
        raw_text = """
Rubro. Renuncia laboral con huella dactilar y firma autografa.

Criterio. Conforme al articulo 802 de la Ley Federal del Trabajo vigente hasta el 30 de noviembre de 2012, una renuncia exhibida en juicio conserva eficacia probatoria plena cuando se demuestra la autenticidad de la firma o de la huella dactilar.

Contexto. El criterio proviene de una contradiccion de tesis resuelta por la Segunda Sala.
""".strip()

        chunks = _split_document(raw_text)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0][0], "Fragmento 1")
        self.assertEqual(chunks[1][0], "Fragmento 2")
        self.assertIn("articulo 802", chunks[1][1].lower())
