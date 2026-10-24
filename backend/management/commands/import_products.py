from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.services import import_shop_file


class Command(BaseCommand):
    help = 'Импорт товаров из YAML-файлов (по умолчанию из папки data)'

    def add_arguments(self, parser):
        parser.add_argument('files', nargs='*', help='Пути к YAML-файлам')

    def handle(self, *args, **options):
        paths = [Path(path) for path in options['files']]
        if not paths:
            paths = sorted((settings.BASE_DIR / 'data').glob('*.yaml'))
        if not paths:
            raise CommandError('Файлы для импорта не найдены')

        for path in paths:
            shop = import_shop_file(path)
            self.stdout.write(f'{path.name}: загружен магазин {shop.name}')
