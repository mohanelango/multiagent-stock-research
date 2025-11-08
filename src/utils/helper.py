def safe_num(val):
    return f"${val:,}" if isinstance(val, (int, float)) else "N/A"
