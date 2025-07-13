from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from api.models import CustomUser
from api.views.authentication import register
from django.urls import reverse
from unittest.mock import patch

class TestRegisterView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.valid_payload = {
            "username": "testuser",
            "district": "01",
            "email": "test@example.com",
            "phone": "1234567890"
        }

    def test_register_success(self):
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], 'Registration Successful')
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(CustomUser.objects.get().username, 'testuser')

    def test_register_missing_username(self):
        payload = self.valid_payload.copy()
        payload.pop('username')
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Please provide username')

    def test_register_missing_district(self):
        payload = self.valid_payload.copy()
        payload.pop('district')
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Please provide a valid district')

    def test_register_missing_email(self):
        payload = self.valid_payload.copy()
        payload.pop('email')
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Please provide a valid email')

    def test_register_duplicate_email(self):
        CustomUser.objects.create(
            username="existing",
            email=self.valid_payload['email'],
            district="01",
            phone_number="9876543210"
        )
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'User with this email already exists')

    def test_register_duplicate_phone(self):
        CustomUser.objects.create(
            username="existing",
            email="other@example.com",
            district="01",
            phone_number=self.valid_payload['phone']
        )
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'User with this phone already exists')

    def test_register_invalid_district(self):
        payload = self.valid_payload.copy()
        payload['district'] = '99'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Invalid district number')

    @patch('api.views.authentication.CustomUser.save')
    def test_register_database_error(self, mock_save):
        mock_save.side_effect = Exception('Database error')
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['message'], 'Database error')
