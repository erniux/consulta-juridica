from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(LLM_PROVIDER="mock")
class RegisterViewTests(APITestCase):
    def test_public_registration_creates_standard_user_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "nuevo_usuario",
                "email": "nuevo@example.com",
                "password": "Consulta12345!",
                "first_name": "Nuevo",
                "last_name": "Usuario",
                "role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username="nuevo_usuario")
        self.assertEqual(user.role, get_user_model().Role.USER)
        self.assertFalse(user.is_superuser)
