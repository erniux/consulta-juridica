from django.test import SimpleTestCase

from .services.classifiers import expand_query, generate_jurisprudence_queries, is_precise_legal_lookup


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

    def test_expand_query_keeps_short_generic_queries_focused(self):
        prompt = "Que es el buzon IMSS?"

        expansions = expand_query(prompt, "social_security", ["seguridad-social"])

        self.assertEqual(expansions[0], prompt)
        self.assertNotIn("seguro social incapacidad trabajo imss", expansions)

    def test_generate_jurisprudence_queries_detects_pregnancy_dismissal(self):
        prompt = "Despidieron a una trabajadora por estar embarazada."

        queries = generate_jurisprudence_queries(prompt, "labor_individual", ["despido-embarazo"])

        self.assertIn(
            "despido embarazo trabajadora embarazada discriminacion maternidad estabilidad laboral",
            queries,
        )
        self.assertIn("embarazo maternidad despido discriminacion estabilidad reforzada", queries)

    def test_generate_jurisprudence_queries_detects_honorarios_subordination(self):
        prompt = "Me corrieron pero me pagaban por honorarios y tenia horario y jefe."

        queries = generate_jurisprudence_queries(
            prompt,
            "labor_individual",
            ["honorarios-subordinacion", "despido"],
        )

        self.assertIn(
            "honorarios subordinacion relacion laboral simulacion prestaciones despido",
            queries,
        )
        self.assertIn("honorarios subordinacion relacion laboral simulada", queries)

    def test_generate_jurisprudence_queries_detects_psychological_harm(self):
        prompt = "Tuve estres y dano psicologico despues del despido."

        queries = generate_jurisprudence_queries(
            prompt,
            "labor_individual",
            ["dano-psicologico", "despido"],
        )

        self.assertIn(
            "despido dano psicologico dano emocional estres laboral hostigamiento acoso",
            queries,
        )
        self.assertIn("dano psicologico estres acoso laboral dano moral trabajador", queries)
