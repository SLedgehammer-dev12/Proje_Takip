PROJECT_TYPE_OPTIONS = [
    "İnşaat",
    "Mekanik",
    "Piping",
    "Elektrik",
    "I&C",
    "Siemens",
    "Diğer",
]

PROJECT_TYPE_OPTIONS_WITH_EMPTY = ["", *PROJECT_TYPE_OPTIONS]
PROJECT_TYPE_FILTER_OPTIONS = [*PROJECT_TYPE_OPTIONS, "Belirtilmemiş"]

PROJECT_TYPE_ALIASES = {
    "İnşaat": ("İnşaat", "inşaat", "Insaat", "insaat"),
    "Mekanik": ("Mekanik", "mekanik", "MEKANIK"),
    "Piping": ("Piping", "piping", "PIPING"),
    "Elektrik": ("Elektrik", "elektrik", "ELEKTRIK"),
    "I&C": ("I&C", "i&c", "Enstrümantasyon", "enstrümantasyon", "Enstrumantasyon", "enstrumantasyon"),
    "Siemens": ("Siemens", "siemens", "SIEMENS"),
    "Diğer": ("Diğer", "diğer", "Diger", "diger", "P&ID", "p&id"),
}

_NORMALIZED_PROJECT_TYPE_MAP = {
    alias.casefold(): canonical
    for canonical, aliases in PROJECT_TYPE_ALIASES.items()
    for alias in aliases
}


def normalize_project_type(value):
    """Normalize free-text project type values to the canonical application list."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return _NORMALIZED_PROJECT_TYPE_MAP.get(normalized.casefold(), "Diğer")


def get_project_type_aliases(value):
    """Return the known aliases that should be treated as the same project type."""
    canonical = normalize_project_type(value)
    if canonical is None:
        return ()
    return PROJECT_TYPE_ALIASES.get(canonical, (canonical,))
