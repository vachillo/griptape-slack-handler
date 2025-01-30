from __future__ import annotations

from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from typing import Callable, TypeVar

    T = TypeVar("T")


async def to_async(func: Callable[..., T], *args, **kwargs) -> T:
    return await asyncio.to_thread(func, *args, **kwargs)


async def to_async_collect(funcs: list[Callable[..., T]]) -> list[T]:
    return await asyncio.gather(*[to_async(func) for func in funcs])
