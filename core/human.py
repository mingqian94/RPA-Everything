"""Human-like pacing helpers shared by browser, desktop, and Android Skills."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable


def jitter(base: float, ratio: float = 0.25, minimum: float = 0.0) -> float:
    delta = abs(base) * ratio
    return max(minimum, random.uniform(base - delta, base + delta))


async def human_pause(min_wait: float = 1.0, max_wait: float = 3.0) -> None:
    await asyncio.sleep(random.uniform(min_wait, max_wait))


def human_sleep(min_wait: float = 0.4, max_wait: float = 1.2) -> None:
    time.sleep(random.uniform(min_wait, max_wait))


async def slow_scroll_browser(
    page,
    rounds: int,
    min_wait: float = 1.4,
    max_wait: float = 3.8,
    min_delta: int = 520,
    max_delta: int = 980,
) -> None:
    for _ in range(max(0, rounds)):
        await page.mouse.wheel(0, random.randint(min_delta, max_delta))
        await human_pause(min_wait, max_wait)


def slow_android_swipe(
    swipe_fn: Callable[[float, float, float, float, int], None],
    rounds: int,
    start: tuple[float, float] = (0.5, 0.78),
    end: tuple[float, float] = (0.5, 0.28),
    duration_ms: int = 650,
) -> None:
    for _ in range(max(0, rounds)):
        sx = min(1.0, max(0.0, jitter(start[0], 0.06)))
        sy = min(1.0, max(0.0, jitter(start[1], 0.05)))
        ex = min(1.0, max(0.0, jitter(end[0], 0.06)))
        ey = min(1.0, max(0.0, jitter(end[1], 0.05)))
        swipe_fn(sx, sy, ex, ey, round(jitter(duration_ms, 0.18, 120)))
        human_sleep(1.0, 2.8)


async def run_with_pacing(
    actions: list[Callable[[], Awaitable[None]]],
    min_wait: float = 0.8,
    max_wait: float = 2.0,
) -> None:
    for action in actions:
        await action()
        await human_pause(min_wait, max_wait)
