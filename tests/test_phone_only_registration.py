"""
Tests unitaires pour l'inscription par téléphone uniquement
"""
import pytest
from django.test import TestCase, override_settings
from django.db.utils import IntegrityError
from tenxyte.models import get_user_model

User = get_user_model()


class PhoneOnlyRegistrationTestCase(TestCase):
    """Tests pour l'inscription avec téléphone uniquement"""

    def setUp(self):
        """Nettoie les utilisateurs avant chaque test"""
        User.objects.all().delete()

    def tearDown(self):
        """Nettoie les utilisateurs après chaque test"""
        User.objects.all().delete()

    def test_create_user_with_phone_only(self):
        """Test de création d'un utilisateur avec téléphone uniquement"""
        user = User.objects.create_user(
            email=None,
            password="SecurePassword123!",
            phone_country_code="33",
            phone_number="612345678",
            first_name="Jean",
            last_name="Dupont"
        )

        self.assertIsNotNone(user.id)
        self.assertIsNone(user.email)
        self.assertEqual(user.phone_country_code, "33")
        self.assertEqual(user.phone_number, "612345678")
        self.assertEqual(user.first_name, "Jean")
        self.assertEqual(user.last_name, "Dupont")
        self.assertEqual(user.full_phone, "+33612345678")
        self.assertTrue(user.check_password("SecurePassword123!"))

    def test_create_user_with_email_only(self):
        """Test de création d'un utilisateur avec email uniquement"""
        user = User.objects.create_user(
            email="test@example.com",
            password="SecurePassword123!",
            first_name="Marie",
            last_name="Martin"
        )

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "test@example.com")
        self.assertIsNone(user.phone_number)
        self.assertEqual(user.first_name, "Marie")
        self.assertEqual(user.last_name, "Martin")
        self.assertTrue(user.check_password("SecurePassword123!"))

    def test_create_user_with_email_and_phone(self):
        """Test de création d'un utilisateur avec email ET téléphone"""
        user = User.objects.create_user(
            email="combined@example.com",
            password="SecurePassword123!",
            phone_country_code="33",
            phone_number="623456789",
            first_name="Paul",
            last_name="Durand"
        )

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "combined@example.com")
        self.assertEqual(user.phone_country_code, "33")
        self.assertEqual(user.phone_number, "623456789")
        self.assertTrue(user.check_password("SecurePassword123!"))

    def test_create_user_without_identifier_fails(self):
        """Test que la création sans identifiant échoue"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(
                password="SecurePassword123!",
                first_name="Test",
                last_name="User"
            )

        self.assertIn("téléphone", str(context.exception).lower())

    def test_duplicate_phone_number_fails(self):
        """Test que les numéros de téléphone en doublon sont refusés"""
        # Créer le premier utilisateur
        User.objects.create_user(
            email=None,
            password="Password1!",
            phone_country_code="33",
            phone_number="634567890",
            first_name="User",
            last_name="One"
        )

        # Tenter de créer un deuxième utilisateur avec le même téléphone
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email=None,
                password="Password2!",
                phone_country_code="33",
                phone_number="634567890",  # Même numéro
                first_name="User",
                last_name="Two"
            )

    def test_same_phone_different_country_code_allowed(self):
        """Test que le même numéro avec un code pays différent est autorisé"""
        user1 = User.objects.create_user(
            email=None,
            password="Password1!",
            phone_country_code="33",  # France
            phone_number="645678901",
            first_name="User",
            last_name="France"
        )

        user2 = User.objects.create_user(
            email=None,
            password="Password2!",
            phone_country_code="32",  # Belgique
            phone_number="645678901",  # Même numéro local
            first_name="User",
            last_name="Belgium"
        )

        self.assertIsNotNone(user1.id)
        self.assertIsNotNone(user2.id)
        self.assertNotEqual(user1.id, user2.id)

    def test_soft_deleted_user_allows_phone_reuse(self):
        """Test que le soft delete permet la réutilisation du téléphone"""
        # Créer un utilisateur
        user1 = User.objects.create_user(
            email=None,
            password="Password1!",
            phone_country_code="33",
            phone_number="656789012",
            first_name="User",
            last_name="Deleted"
        )
        user1_id = user1.id

        # Soft delete
        user1.soft_delete()
        user1.refresh_from_db()
        self.assertTrue(user1.is_deleted)

        # Créer un nouvel utilisateur avec le même téléphone
        user2 = User.objects.create_user(
            email=None,
            password="Password2!",
            phone_country_code="33",
            phone_number="656789012",  # Même numéro
            first_name="User",
            last_name="New"
        )

        self.assertIsNotNone(user2.id)
        self.assertNotEqual(user1_id, user2.id)
        self.assertFalse(user2.is_deleted)

    def test_user_str_with_phone_only(self):
        """Test de la représentation string d'un utilisateur avec téléphone uniquement"""
        user = User.objects.create_user(
            email=None,
            password="Password!",
            phone_country_code="33",
            phone_number="667890123",
            first_name="Test",
            last_name="String"
        )

        self.assertEqual(str(user), "+33667890123")

    def test_user_str_with_email(self):
        """Test de la représentation string d'un utilisateur avec email"""
        user = User.objects.create_user(
            email="string@example.com",
            password="Password!",
            first_name="Test",
            last_name="String"
        )

        self.assertEqual(str(user), "string@example.com")

    def test_user_str_with_both(self):
        """Test que l'email est prioritaire dans la représentation string"""
        user = User.objects.create_user(
            email="priority@example.com",
            password="Password!",
            phone_country_code="33",
            phone_number="678901234",
            first_name="Test",
            last_name="Priority"
        )

        # L'email doit être prioritaire
        self.assertEqual(str(user), "priority@example.com")

    def test_email_normalization_when_provided(self):
        """Test que l'email est normalisé quand fourni"""
        user = User.objects.create_user(
            email="TeSt@ExAmPlE.CoM",
            password="Password!",
            first_name="Test",
            last_name="Normalize"
        )

        # L'email doit être en minuscules
        self.assertEqual(user.email, "test@example.com")

    def test_no_email_normalization_when_none(self):
        """Test qu'il n'y a pas d'erreur quand l'email est None"""
        user = User.objects.create_user(
            email=None,
            password="Password!",
            phone_country_code="33",
            phone_number="689012345",
            first_name="Test",
            last_name="NoEmail"
        )

        self.assertIsNone(user.email)


class PhoneRegistrationAPITestCase(TestCase):
    """Tests d'intégration pour l'API d'inscription par téléphone"""

    def setUp(self):
        """Nettoie les utilisateurs avant chaque test"""
        User.objects.all().delete()

    def test_register_serializer_accepts_phone_only(self):
        """Test que le RegisterSerializer accepte téléphone uniquement"""
        from tenxyte.serializers import RegisterSerializer

        data = {
            "phone_country_code": "33",
            "phone_number": "690123456",
            "password": "SecurePassword123!",
            "first_name": "API",
            "last_name": "Test"
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["phone_country_code"], "33")
        self.assertEqual(serializer.validated_data["phone_number"], "690123456")
        self.assertIsNone(serializer.validated_data.get("email"))

    def test_register_serializer_requires_identifier(self):
        """Test que le RegisterSerializer exige un identifiant"""
        from tenxyte.serializers import RegisterSerializer

        data = {
            "password": "SecurePassword123!",
            "first_name": "API",
            "last_name": "Test"
        }

        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Email or phone number is required", str(serializer.errors))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
