# apps/super_admin/management/commands/setup_super_admin.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.super_admin.models import AdminUser

class Command(BaseCommand):
    help = 'Setup initial super admin user'
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        email = input("Enter super admin email: ")
        password = input("Enter super admin password: ")
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            
            AdminUser.objects.create(
                user=user,
                role='super_admin',
                permissions={'all': True}
            )
            
            self.stdout.write(self.style.SUCCESS(f'Super admin {email} created!'))
        else:
            self.stdout.write(self.style.WARNING(f'User {email} already exists'))