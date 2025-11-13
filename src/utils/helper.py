def safe_num(val, reported_currency: str = ""):
    """
    Format numeric values with thousands separator and prepend the reported currency
    (if provided and valid). Returns 'N/A' for missing or invalid inputs.
    """
    if isinstance(val, (int, float)):
        prefix = f" {reported_currency}" if reported_currency else ""
        return f"{val:,.0f}{prefix}"
    return "N/A"

