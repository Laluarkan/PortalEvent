from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(user_signed_up)
def user_signed_up_(request, user, **kwargs):
    # Logika: Setiap ada user baru yang daftar lewat Google (Social Account),
    # otomatis jadikan dia Organizer.
    user.is_organizer = True
    user.save()