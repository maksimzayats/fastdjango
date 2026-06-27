from modern_python_template.entrypoints.fastapi.bootstrap import container
from modern_python_template.entrypoints.fastapi.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
app = api_factory(include_django=True)
