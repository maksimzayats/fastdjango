from collections.abc import Callable, Hashable
from concurrent.futures import ThreadPoolExecutor, as_completed

_MAX_PARALLEL_WORKERS = 8


def _resolve_in_parallel[ResolveKey: Hashable, ResolveValue](
    *,
    entries: tuple[ResolveKey, ...],
    resolver: Callable[[ResolveKey], ResolveValue],
) -> dict[ResolveKey, ResolveValue]:
    if not entries:
        return {}

    max_workers = min(_MAX_PARALLEL_WORKERS, len(entries))
    resolved_entries: dict[ResolveKey, ResolveValue] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(resolver, entry): entry for entry in entries}
        for future in as_completed(futures):
            entry = futures[future]
            resolved_entries[entry] = future.result()

    return resolved_entries
