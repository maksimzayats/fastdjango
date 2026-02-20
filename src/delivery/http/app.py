from delivery.http.bootstrap import container
from delivery.http.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
app = api_factory(include_django=True)
