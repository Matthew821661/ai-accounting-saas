
def calculate_vat(amount, vat_type):
    if vat_type == "standard":
        return round(amount * 0.15, 2), "standard"
    elif vat_type == "zero":
        return 0.0, "zero-rated"
    return 0.0, "exempt"
