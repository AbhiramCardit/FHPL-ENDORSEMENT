"""Domain-specific business rules per insuree."""


def apply_business_rules(record: dict, insuree_config: dict) -> dict:
    """Apply configurable business rules. Returns validation result dict."""
    raise NotImplementedError
