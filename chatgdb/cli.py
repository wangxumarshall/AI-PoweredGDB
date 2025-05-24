import argparse
from os.path import abspath, dirname
from inspect import getfile, currentframe
from urllib.request import Request, urlopen
import json
import sys # Import sys for stderr

PATH = dirname(abspath(getfile(currentframe())))


def set_key(key):
    """Set the api key for ChatGDB"""
    with open(PATH + "/.secret.txt", "w") as f:
        f.write("OPENAI_KEY=\"" + key + "\"")


def set_model(model):
    """Set the model for ChatGDB"""
    with open(PATH + "/.model.txt", "w") as f:
        f.write("MODEL=\"" + model + "\"")

def set_url(url):
    """Set the url for ChatGDB"""
    with open(PATH + "/.url.txt", "w") as f:
        f.write("URL=\"" + url + "\"")

def version():
    """Return version information"""
    with urlopen(Request("https://pypi.org/pypi/chatgdb/json"), timeout=10) as f:
        return json.load(f)["info"]["version"]


def main():
    parser = argparse.ArgumentParser(
        description="Configure ChatGDB, the GDB chatbot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-k',
        "--key",
        type=str,
        help="Provide an api key for ChatGDB")
    parser.add_argument(
        '-m',
        "--model",
        type=str,
        choices=["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini", "custom_gdb_model"],
        help="Provide a model for ChatGDB (gpt-3.5-turbo, gpt-4, gpt-4o, gpt-4o-mini, o1-preview, o1-mini, custom_gdb_model)",
        default="gpt-3.5-turbo"
    )
    parser.add_argument(
        '-u',
        "--url",
        type=str,
        help="Provide a API url for ChatGDB",
        default="https://api.openai.com/v1/chat/completions"
    )
    parser.add_argument(
        '-v',
        "--version",
        action="version",
        version="%(prog)s " + version(),
        help="Print the version of ChatGDB")

    args = parser.parse_args()

    try:
        if args.key:
            set_key(args.key)
            print(f"API key set successfully. Stored in {PATH}/.secret.txt")

        if args.model:
            set_model(args.model)
            print(f"Model set to {args.model}. Stored in {PATH}/.model.txt")

        if args.url:
            set_url(args.url)
            print(f"URL set to {args.url}. Stored in {PATH}/.url.txt")

        # Display current configuration if no arguments are passed
        if not any(vars(args).values()): # Check if any arguments were passed
            print("Current ChatGDB Configuration:")
            try:
                key = utils.get_key()
                print(f"  API Key: {'*' * (len(key) - 4) + key[-4:] if key else 'Not set'}")
            except FileNotFoundError as e:
                print(f"  API Key: Not set ({e})")
            try:
                model = utils.get_model()
                print(f"  Model: {model if model else 'Not set'}")
            except FileNotFoundError as e:
                print(f"  Model: Not set ({e})")
            try:
                url = utils.get_url()
                print(f"  URL: {url if url else 'Not set'}")
            except FileNotFoundError as e:
                print(f"  URL: Not set ({e})")
            print("\nUse 'chatgdb -h' for options to set or update these values.")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr) # Print to stderr
        sys.exit(1) # Exit with a non-zero status to indicate an error
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
