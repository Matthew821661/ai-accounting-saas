def classify_transaction(desc):
    desc = str(desc).lower()
    if "fuel" in desc:
        return "6400/000 - Travel"
    elif "rent" in desc:
        return "6200/000 - Rent"
    elif "woolworths" in desc:
        return "6500/000 - Staff Welfare"
    elif "education" in desc:
        return "6700/000 - Education"
    else:
        return "9999/999 - Uncategorized"