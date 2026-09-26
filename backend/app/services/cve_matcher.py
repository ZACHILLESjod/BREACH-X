import re


_VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+)*)(.*)$", re.IGNORECASE)
_PRE_RELEASE = re.compile(r"^(?:[-_.]?(dev|alpha|a|beta|b|rc|pre|preview))(.*)$", re.IGNORECASE)
_POST_RELEASE = re.compile(r"^(?:[-_.]?(post|patch|p|rev|r))(.*)$", re.IGNORECASE)


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _version_key(version: str) -> tuple:
    """Build an ordering key for numeric dotted versions and common release tags."""
    value = version.strip()
    if not value:
        raise ValueError("Version cannot be empty")

    # Build metadata does not affect precedence (for example, 1.2.0+build.4).
    value = value.split("+", 1)[0]
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"Unsupported version format: {version!r}")

    release_parts = [int(part) for part in match.group(1).split(".")]
    # 1.2 and 1.2.0 represent the same release; preserve internal zeroes.
    while len(release_parts) > 1 and release_parts[-1] == 0:
        release_parts.pop()
    release = tuple(release_parts)
    suffix = match.group(2).lower()

    if not suffix:
        return release, 0, ()  # final release

    pre_match = _PRE_RELEASE.fullmatch(suffix)
    if pre_match:
        label = pre_match.group(1).lower()
        rank = -2 if label == "dev" else -1
        details = pre_match.group(2)
    else:
        post_match = _POST_RELEASE.fullmatch(suffix)
        if post_match:
            rank = 1
            details = post_match.group(2)
        else:
            # Treat an unrecognized suffix as a prerelease so it does not sort
            # after the corresponding stable release and create false matches.
            rank = -1
            details = suffix.lstrip("-_.")

    tokens = re.findall(r"\d+|[a-z]+", details)
    token_key = tuple((0, int(token)) if token.isdigit() else (1, token) for token in tokens)
    return release, rank, token_key


def match_vulnerability(
    software_name: str,
    software_version: str,
    affected_software: str,
    min_version: str | None,
    max_version: str | None,
    min_version_inclusive: bool = True,
    max_version_inclusive: bool = True,
) -> bool:
    """Return whether software matches the affected name and version interval."""
    if _normalized_name(software_name) != _normalized_name(affected_software):
        return False

    try:
        installed = _version_key(software_version)
        minimum = _version_key(min_version) if min_version is not None else None
        maximum = _version_key(max_version) if max_version is not None else None
    except (AttributeError, TypeError, ValueError):
        return False

    above_minimum = (
        True
        if minimum is None
        else installed >= minimum if min_version_inclusive else installed > minimum
    )
    below_maximum = (
        True
        if maximum is None
        else installed <= maximum if max_version_inclusive else installed < maximum
    )
    return above_minimum and below_maximum


def match_affected_products(
    software_name: str,
    software_version: str,
    affected_products,
) -> bool:
    """Match if any independent affected-product/version entry matches."""
    for product in affected_products:
        # Pydantic models and dictionaries are both accepted to keep this
        # helper convenient for API and service-level callers.
        get_value = product.get if isinstance(product, dict) else lambda key, default=None: getattr(product, key, default)
        affected_software = get_value("affected_software")
        if not affected_software:
            continue
        names = {affected_software}
        product_name = get_value("product")
        edition = get_value("edition")
        vendor = get_value("vendor")
        if product_name:
            names.add(product_name)
            names.add(f"{product_name} {edition}" if edition else product_name)
        if vendor and product_name:
            names.add(f"{vendor} {product_name} {edition}" if edition else f"{vendor} {product_name}")

        range_matches = any(
            match_vulnerability(
                software_name,
                software_version,
                name,
                get_value("min_version"),
                get_value("max_version"),
                get_value("min_version_inclusive", True) is not False,
                get_value("max_version_inclusive", True) is not False,
            )
            for name in names
        )
        if range_matches:
            return True
    return False


if __name__ == "__main__":
    result = match_vulnerability(
        "Apache HTTP Server", "2.4.50", "Apache HTTP Server", "2.4.0", "2.4.49"
    )
    print("Vulnerability Match:", result)
