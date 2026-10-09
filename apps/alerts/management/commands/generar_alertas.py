"""Genera las alertas de cada barbería operativa. Se programa con cron en el despliegue.

Barbershop no es una tabla de negocio (no hereda de TenantScopedModel), así que
recorrerla no necesita `unscoped`. Cada barbería corre en su propio tenant_context
(barreras 1 y 2) y con "hoy" en su zona horaria.
"""

import logging
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.alerts.services import generate_alerts
from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Barbershop

logger = logging.getLogger(__name__)

OPERATIONAL = (Barbershop.Status.TRIAL, Barbershop.Status.ACTIVE)


class Command(BaseCommand):
    help = "Genera y resuelve alertas de inventario y fiados vencidos en cada barbería operativa."

    def handle(self, *args, **options) -> None:
        shops = Barbershop.objects.filter(status__in=OPERATIONAL).order_by("pk")
        failures = sum(not self._run_for(shop) for shop in shops)
        if failures:
            raise CommandError(f"{failures} barbería(s) con error.")

    def _run_for(self, shop: Barbershop) -> bool:
        today = timezone.now().astimezone(ZoneInfo(shop.timezone)).date()
        try:
            with tenant_context(shop.pk):
                result = generate_alerts(today)
        except Exception:
            # Una barbería con problemas no detiene a las demás; el detalle queda en el log.
            logger.exception("No se pudieron generar las alertas de la barbería %s", shop.pk)
            self.stderr.write(f"{shop.slug}: error (ver log)")
            return False
        created = sum(result["created"].values())
        self.stdout.write(
            f"{shop.slug} ({today}): {created} alertas nuevas, {result['resolved']} resueltas, "
            f"{result['overdue_marked']} fiados vencidos"
        )
        return True
