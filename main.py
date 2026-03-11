from scanner import collect_file_metadata
import sys
import json

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    files = collect_file_metadata(root)

    print(json.dumps(files, indent=2))
    print(f"\nTotal files found: {len(files)}")

if __name__ == "__main__":
    main()