from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailBackend(ModelBackend):
    """Authenticate using email instead of username."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # 'username' field dari form login berisi email
            user = User.objects.get(email__iexact=username)
            if check_password(password, user.password):
                return user
        except User.DoesNotExist:
            return None