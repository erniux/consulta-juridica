from django.db import models


try:
    from pgvector.django import VectorField as PgVectorField
except ImportError:  # pragma: no cover - fallback for environments without pgvector.
    class VectorField(models.JSONField):
        def __init__(self, *args, dimensions=None, **kwargs):
            self.dimensions = dimensions
            super().__init__(*args, **kwargs)


else:
    class VectorField(PgVectorField):
        def __init__(self, *args, dimensions=16, **kwargs):
            super().__init__(*args, dimensions=dimensions, **kwargs)
