import sys

from fetch_competition import get_competition
from fetch_competition_list import get_competition_list
from sams_api_client import CACHE_LOCK, ENDPOINT_CACHE


def get_deep_size_bytes(value, seen: set[int] | None = None) -> int:
    if seen is None:
        seen = set()

    object_id = id(value)
    if object_id in seen:
        return 0
    seen.add(object_id)

    size = sys.getsizeof(value)

    if isinstance(value, dict):
        size += sum(get_deep_size_bytes(key, seen) + get_deep_size_bytes(item, seen) for key, item in value.items())
        return size

    if isinstance(value, (list, tuple, set, frozenset)):
        size += sum(get_deep_size_bytes(item, seen) for item in value)

    return size


def get_cache_size_mb() -> float:
    with CACHE_LOCK:
        return get_deep_size_bytes(ENDPOINT_CACHE) / (1024 * 1024)


def warm_cache() -> None:
    competition_list = get_competition_list()
    total = len(competition_list)

    print(f"Loaded competition list with {total} competitions")
    print(f"Cache size: {get_cache_size_mb():.2f} MB")

    for index, competition in enumerate(competition_list, start=1):
        competition_uuid = competition["uuid"]
        try:
            _, was_cached = get_competition(competition_uuid)
        except Exception:
            print(f"[{index}/{total}] Failed to load competition {competition_uuid}")
            continue

        if was_cached:
            continue

        print(
            f"[{index}/{total}] Loaded competition {competition_uuid} "
            f"cache size: {get_cache_size_mb():.2f} MB"
        )

    print(
        f"Warm cache finished: loaded {total} competitions, "
        f"final cache size: {get_cache_size_mb():.2f} MB"
    )
