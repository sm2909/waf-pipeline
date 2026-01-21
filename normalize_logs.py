import re
from parse_logs import parse_log_line

ALLOWED_PREFIXES = (
    "/rest/",
    "/api/"
)

def is_allowed_path(path):
    return path.startswith(ALLOWED_PREFIXES)

def normalize_path(path):
    # Replace numeric IDs
    path = re.sub(r'\b\d+\b', '<NUM>', path)

    # Replace hashes / tokens
    path = re.sub(r'[a-f0-9]{32,}', '<HASH>', path)

    # Replace query parameter values
    path = re.sub(r'=(?:[^&]{1,50})', '=<VAL>', path)
 
    return path

def main():
    input_file = "data/raw_logs/juice-shop-access.log"
    output_file = "data/benign_dataset.txt"

    kept = 0
    skipped = 0

    with open(input_file, "r") as f, open(output_file, "w") as out:
        for line in f:
            parsed = parse_log_line(line)
            if not parsed:
                continue

            path = parsed["path"]

            if not is_allowed_path(path):
                skipped += 1
                continue

            normalized_path = normalize_path(path)
            has_query = "?" in normalized_path
            text = f"METHOD={parsed['method']} PATH={normalized_path} QUERY={has_query}"
            out.write(text + "\n")
            kept += 1

    print(f"Kept {kept} API requests")
    print(f"Skipped {skipped} non-API requests")

if __name__ == "__main__":
    main()
