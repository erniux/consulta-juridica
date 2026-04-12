from django.test import SimpleTestCase

from .services.classifiers import expand_query, is_precise_legal_lookup


class ClassifierTests(SimpleTestCase):
    def test_precise_legal_lookup_detects_article_and_source_references(self):
        self.assertTrue(
            is_precise_legal_lookup(
                "Que dice el articulo 15 de la Ley del Seguro Social sobre obligaciones del patron?"
            )
        )

    def test_expand_query_does_not_add_generic_expansions_for_precise_lookup(self):
        prompt = "Que dice el articulo 15 de la Ley del Seguro Social sobre obligaciones del patron?"

        expansions = expand_query(prompt, "social_security", ["seguridad-social"])

        self.assertEqual(expansions[0], prompt)
        self.assertNotIn("seguro social incapacidad trabajo imss", expansions)
