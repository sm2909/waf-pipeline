import re

LOG_PATTERN = re.compile(
    r'"(?P<method>GET|POST|PUT|DELETE) (?P<path>\S+) HTTP'
)

def parse_log_line(line):
    match = LOG_PATTERN.search(line)
    if not match:
        return None
    return match.groupdict()

def main():
    input_file = "data/raw_logs/juice-shop-access.log"
    parsed = []

    with open(input_file, "r") as f:
        for line in f:
            result = parse_log_line(line)
            if result:
                parsed.append(result)

    print(f"Parsed {len(parsed)} requests")

    # show a few samples
    for p in parsed[:5]:
        print(p)

if __name__ == "__main__":
    main()
