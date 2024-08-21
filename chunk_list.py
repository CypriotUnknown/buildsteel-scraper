from typing import List, TypeVar

T = TypeVar("T")


def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]
