def estimate_eta_from_address(address: str) -> str:
    """Rough ETA estimate based on keywords in the address."""
    address = address.lower()
    # Sample zones and ETA in minutes
    zones = {
        "ikeja": 30,
        "lekki": 45,
        "ajah": 50,
        "wuse": 40,
        "yaba": 35,
        "festac": 40,
        "surulere": 35,
        "egbeda": 50,
        "ikoyi": 30,
        "maryland": 30,
    }

    for zone, time in zones.items():
        if zone in address:
            return f"{time}–{time + 15} minutes"

    # Default fallback
    return "45–60 minutes"
