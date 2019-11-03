from django.apps import AppConfig

class FuskarConfig(AppConfig):
    name = 'fuskar'

    def ready(self):
        import fuskar.signals
        # generate PCA plot
        from fuskar.utils.helpers import generate_pca_plot
        from django.conf import settings
        generate_pca_plot(settings.PCA_GRAPH, settings.ENCODING_LIST)
