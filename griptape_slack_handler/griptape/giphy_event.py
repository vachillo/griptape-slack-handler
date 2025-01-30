from __future__ import annotations

from typing import Optional
from attrs import define, field, Factory

from griptape.events import BaseEvent


@define
class GiphyEvent(BaseEvent):
    url: str = field()
    title: str = field()
    tag: str = field()
