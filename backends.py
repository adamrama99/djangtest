from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model

User = get_user_model()

class MyCustomBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
            # Gunakan check_password() milik Django
            # Ini akan otomatis mendeteksi apakah hash-nya bcrypt atau PBKDF2
            if check_password(password, user.password):
                return user
        except User.DoesNotExist:
            return None