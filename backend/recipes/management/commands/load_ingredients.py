import csv
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from CSV or JSON file'

    def add_arguments(self, parser):
        path = os.path.join(settings.BASE_DIR, 'data/ingredients.csv')
        parser.add_argument(
            '--file',
            type=str,
            help='Path to the ingredients file (CSV or JSON)',
            default=path,
        )

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File {file_path} does not exist')
            )
            return

        if file_path.endswith('.csv'):
            self._load_from_csv(file_path)
        elif file_path.endswith('.json'):
            self._load_from_json(file_path)
        else:
            self.stdout.write(
                self.style.ERROR('File must be either CSV or JSON')
            )

    def _load_from_csv(self, file_path):
        with open(file_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            ingredients = []
            for row in reader:
                if len(row) == 2:
                    name, measurement_unit = row
                    ingredients.append(
                        Ingredient(
                            name=name.strip(),
                            measurement_unit=measurement_unit.strip()
                        )
                    )
            self._bulk_create_ingredients(ingredients)

    def _load_from_json(self, file_path):
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
            ingredients = []
            for item in data:
                if 'name' in item and 'measurement_unit' in item:
                    ingredients.append(
                        Ingredient(
                            name=item['name'].strip(),
                            measurement_unit=item['measurement_unit'].strip()
                        )
                    )
            self._bulk_create_ingredients(ingredients)

    def _bulk_create_ingredients(self, ingredients):
        if not ingredients:
            self.stdout.write(
                self.style.WARNING('No ingredients found in file')
            )
            return

        created = 0
        for ingredient in ingredients:
            obj, is_created = Ingredient.objects.get_or_create(
                name=ingredient.name,
                measurement_unit=ingredient.measurement_unit
            )
            if is_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created} new ingredients'
            )
        )
