from collections import OrderedDict

# Palette: display name → hex
PALETTE: OrderedDict[str, str] = OrderedDict([
    ("Red",         "#FF3B30"),
    ("Orange",      "#FF9500"),
    ("Yellow",      "#FFCC00"),
    ("Green",       "#34C759"),
    ("Mint",        "#00C7BE"),
    ("Teal",        "#30B0C7"),
    ("Cyan",        "#32ADE6"),
    ("Blue",        "#007AFF"),
    ("Indigo",      "#5856D6"),
    ("Purple",      "#AF52DE"),
    ("Pink",        "#FF2D55"),
    ("Rose",        "#FF6B8A"),
    ("Coral",       "#FF6B35"),
    ("Brown",       "#A2845E"),
    ("Beige",       "#F5E6D3"),
    ("Gold",        "#FFD60A"),
    ("Olive",       "#6B7C3A"),
    ("Maroon",      "#800020"),
    ("Navy",        "#1D3461"),
    ("Black",       "#1C1C1E"),
    ("Charcoal",    "#3A3A3C"),
    ("Gray",        "#8E8E93"),
    ("Silver",      "#C7C7CC"),
    ("White",       "#F5F5F7"),
])


def hex_for(name: str) -> str:
    """Return the hex code for a palette name, or gray fallback."""
    if name and name.startswith("#"):
        return name
    return PALETTE.get(name, "#8E8E93")


def is_light(hex_: str) -> bool:
    """Return True if the color is light (needs dark border/text)."""
    h = hex_.lstrip("#")
    if len(h) < 6:
        return False
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.65


def all_names() -> list[str]:
    return list(PALETTE.keys())
