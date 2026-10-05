# apps/accounts/pipeline.py
from django.contrib.auth import get_user_model

User = get_user_model()


def associate_by_email(backend, details, user=None, *args, **kwargs):
    """
    If a User with the same email already exists, reuse it instead of
    trying to create a new one.
    """
    if user:
        return None

    email = details.get('email')
    if not email:
        return None

    try:
        existing = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        return None

    return {'user': existing, 'is_new': False}


def create_profile(backend, user, is_new=False, *args, **kwargs):
    """
    Ensure every user created or authenticated via social auth has a Profile.
    Runs on every social-auth login; get_or_create makes it idempotent.
    """
    if not user:
        return None

    from apps.accounts.models import Profile

    Profile.objects.get_or_create(user=user)
    return None
