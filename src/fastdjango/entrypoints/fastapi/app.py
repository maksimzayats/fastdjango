from fastdjango.entrypoints.fastapi.bootstrap import container
from fastdjango.entrypoints.fastapi.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
app = api_factory(include_django=True)
