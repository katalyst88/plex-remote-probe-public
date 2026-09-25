from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccountTests(TestCase):
    def test_signup_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"username": "newbie", "email": "New@Example.com", "password1": "a-long-Pass-9", "password2": "a-long-Pass-9"},
        )
        self.assertRedirects(response, reverse("boards:index"))
        user = User.objects.get(username="newbie")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_rejected(self):
        User.objects.create_user("first", email="dup@example.com", password="x-long-pass-1")
        response = self.client.post(
            reverse("accounts:signup"),
            {"username": "second", "email": "DUP@example.com", "password1": "a-long-Pass-9", "password2": "a-long-Pass-9"},
        )
        self.assertContains(response, "already exists")

    def test_profile_and_edit(self):
        user = User.objects.create_user("carol", password="x-long-pass-1")
        self.client.force_login(user)
        self.client.post(reverse("accounts:edit_profile"), {"display_name": "Carol D", "location": "Perth", "bio": "hi"})
        response = self.client.get(reverse("accounts:profile", args=["carol"]))
        self.assertContains(response, "Carol D")
        self.assertContains(response, "Perth")

    def test_logout_requires_post(self):
        user = User.objects.create_user("dan", password="x-long-pass-1")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
