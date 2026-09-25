from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone


class User(AbstractUser):
    """Forum member.

    Membership fields are the hook for the paid subscription: a payment
    provider webhook will set ``membership_tier`` and ``membership_expires_at``.
    """

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        MEMBER = "member", "Member"

    display_name = models.CharField(max_length=60, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=80, blank=True)
    membership_tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE)
    membership_expires_at = models.DateTimeField(null=True, blank=True)

    @property
    def name(self):
        return self.display_name or self.username

    @property
    def initials(self):
        parts = self.name.split()
        letters = "".join(p[0] for p in parts[:2]) if parts else "?"
        return letters.upper()

    @property
    def has_active_membership(self):
        if self.is_staff:
            return True
        if self.membership_tier == self.Tier.FREE:
            return False
        return self.membership_expires_at is None or self.membership_expires_at > timezone.now()

    def get_absolute_url(self):
        return reverse("accounts:profile", args=[self.username])

    def __str__(self):
        return self.username
