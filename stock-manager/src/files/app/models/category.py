"""app/models/category.py — Category and PartType value objects."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PartTypeConfig:
    id: int
    category_id: int
    key: str           # DB key e.g. "JK_INCELL_FHD"
    name: str          # Display label e.g. "(JK) incell FHD"
    accent_color: str  # Hex e.g. "#4A9EFF"
    sort_order: int


@dataclass
class CategoryConfig:
    id: int
    key: str              # e.g. "displays"
    name_en: str
    name_de: str
    name_ar: str
    sort_order: int
    icon: str
    is_active: bool
    part_types: list[PartTypeConfig] = field(default_factory=list)

    def name(self, lang: str = "EN") -> str:
        return {"EN": self.name_en, "DE": self.name_de, "AR": self.name_ar}.get(lang, self.name_en)
