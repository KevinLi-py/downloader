def parse_headers(string: str) -> dict:
    return {key.strip(): value.strip() for line in string.strip().splitlines()
            for key, value in (line.split(':', 2),)}
