"""
Executor de testes do LavaFlow.

 Este executor roda o database/01_ddl.sql no banco de testes logo depois de criá-lo, para que
os testes usem exatamente a mesma estrutura do banco real.

Uso:
    python manage.py test --testrunner core.test_runner.LavaFlowTestRunner
"""
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner


class LavaFlowTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        configuracao = super().setup_databases(**kwargs)
        ddl = (Path(settings.BASE_DIR) / "database" / "01_ddl.sql").read_text(encoding="utf-8")
        for conexao in connections.all():
            with conexao.cursor() as cursor:
                cursor.execute(ddl)
        return configuracao