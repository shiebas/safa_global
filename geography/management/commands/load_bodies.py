from django.core.management.base import BaseCommand
from geography.models import GoverningBody

BODIES = [
    {
        'name': 'Fédération Internationale de Football Association',
        'acronym': 'FIFA',
        'headquarters': 'Zurich, Switzerland',
        'founded_date': '1904-05-21',
        'website': 'https://www.fifa.com'
    },
    {
        'name': 'World Rugby',
        'acronym': 'WR',
        'headquarters': 'Dublin, Ireland',
        'website': 'https://www.world.rugby'
    }
]

class Command(BaseCommand):
    help = 'Loads initial governing bodies'

    def handle(self, *args, **options):
        for body in BODIES:
            GoverningBody.objects.get_or_create(
                acronym=body['acronym'],
                defaults=body
            )
        self.stdout.write(self.style.SUCCESS('Successfully loaded governing bodies'))