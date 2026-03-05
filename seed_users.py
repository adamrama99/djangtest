import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
sys.path.insert(0, r'd:\code\django_its\djangtest')
django.setup()

from django.contrib.auth.models import User, Group

admin_group, _ = Group.objects.get_or_create(name='admin')
staff_group, _ = Group.objects.get_or_create(name='staff')

admin_user = User.objects.get(username='admin')
admin_user.groups.add(admin_group)

if not User.objects.filter(username='staff').exists():
    staff_user = User.objects.create_user('staff', '', 'staff123')
    staff_user.first_name = 'Staff'
    staff_user.last_name = 'User'
    staff_user.save()
else:
    staff_user = User.objects.get(username='staff')
staff_user.groups.add(staff_group)

print('Groups created: admin, staff')
print(f'admin groups: {list(admin_user.groups.values_list("name", flat=True))}')
print(f'staff groups: {list(staff_user.groups.values_list("name", flat=True))}')
