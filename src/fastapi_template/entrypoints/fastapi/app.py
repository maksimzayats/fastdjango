from fastapi_template.entrypoints.fastapi.bootstrap import container
from fastapi_template.entrypoints.fastapi.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
app = api_factory()
