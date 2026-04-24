from fastdjango.core.shared.delivery.fastapi.bootstrap import container
from fastdjango.core.shared.delivery.fastapi.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
app = api_factory(include_django=True)
