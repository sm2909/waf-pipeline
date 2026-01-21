def tokenize(line):
    line = line.strip()
    line = line.replace("METHOD=", "method_")
    line = line.replace("PATH=", "path_")
    line = line.replace("/", " / ")
    line = line.replace("?", " ? ")
    line = line.replace("=", " = ")
    line = line.replace("&", " & ")
    return " ".join(line.split())

def main():
    infile = "data/benign_dataset.txt"
    outfile = "data/train_tokens.txt"

    with open(infile) as f, open(outfile, "w") as out:
        for line in f:
            out.write(tokenize(line) + "\n")

    print("Tokenized training data created")

if __name__ == "__main__":
    main()
