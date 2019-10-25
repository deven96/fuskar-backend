from django.apps import AppConfig


class FuskarConfig(AppConfig):
    name = 'fuskar'

    def ready(self):
        import fuskar.signals

        # fuskar.signals.test_attendance()
