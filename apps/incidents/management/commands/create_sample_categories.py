from django.core.management.base import BaseCommand
from apps.incidents.models import Category


class Command(BaseCommand):
    help = 'Creates sample incident categories'

    def handle(self, *args, **options):
        categories = [
            {'name': 'Medical Emergency', 'description': 'Health-related emergencies requiring immediate medical attention'},
            {'name': 'Fire', 'description': 'Fire incidents and fire-related emergencies'},
            {'name': 'Security', 'description': 'Security threats, breaches, or safety concerns'},
            {'name': 'Infrastructure', 'description': 'Infrastructure issues, utilities, or facility problems'},
            {'name': 'Natural Disaster', 'description': 'Natural disasters like floods, earthquakes, storms'},
            {'name': 'Accident', 'description': 'Accidents and incidents involving vehicles or equipment'},
            {'name': 'Other', 'description': 'Other types of incidents not covered above'},
        ]

        created_count = 0
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {category.name}'))

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} new category(ies).'))

