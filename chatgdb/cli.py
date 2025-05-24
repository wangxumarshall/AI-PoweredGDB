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

    # Attempt to load existing config to check if files exist before writing
    # This is more for robust initialization than just writing new files
    try:
        # These calls are primarily for their side effect of checking file existence if no args are given
        # If utils.py's get_key/model/url are called at module load time for HEADERS/URL,
        # an error might occur there first if files are missing.
        # This depends on Python's import and execution order.
        from chatgdb import utils # Ensure utils is imported to access its functions
        if not any([args.key, args.model, args.url]):
             # Check if essential config is missing if no arguments are passed to set them
            try:
                utils.get_key() 
                utils.get_model()
                utils.get_url()
            except FileNotFoundError as e:
                print(f"Configuration error: {e}", file=sys.stderr)
                print("Please configure ChatGDB using -k, -m, or -u options.", file=sys.stderr)
                parser.print_help()
                sys.exit(1)

    except ImportError:
        print("Error: Could not import ChatGDB utilities. Ensure ChatGDB is installed correctly.", file=sys.stderr)
        sys.exit(1)

    if args.key:
        set_key(args.key)
        print(f"API key set in {PATH}/.secret.txt")
    if args.model:
        set_model(args.model)
        print(f"Model set to '{args.model}' in {PATH}/.model.txt")
    if args.url:
        set_url(args.url)
        print(f"API URL set to '{args.url}' in {PATH}/.url.txt")

    if not any([args.key, args.model, args.url]):
        # This part will now likely be preceded by the check above if config files are missing
        print("No configuration options provided. Current settings (if any) will be used.")
        # parser.print_help() # Avoid printing help if config exists and no args given


if __name__ == "__main__":
    main()
