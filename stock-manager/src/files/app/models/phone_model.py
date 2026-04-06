"""app/models/phone_model.py — PhoneModel value object."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PhoneModel:
    id: int
    brand: str
    name: str
    sort_order: int
