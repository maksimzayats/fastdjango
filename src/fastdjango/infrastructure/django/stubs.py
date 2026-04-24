import django_stubs_ext


def patch_django_stubs() -> None:
    django_stubs_ext.monkeypatch()
