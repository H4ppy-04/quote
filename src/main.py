#!/usr/bin/env python

"""
A quoting program to be used privately on Linux
Copyright © 2024 Joshua Rose <joshuarose (at) gmx (dot) com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import argparse
import json
import random
import subprocess
import sys
from dataclasses import dataclass
from shutil import which
from typing import Optional


class Parser:

    def __init__(self):
        self.argument_parser = argparse.ArgumentParser()

        self.argument_parser.add_argument(
            "--color",
            choices=["always", "never", "auto"],
            nargs="?",
            help="Color text output",
        )

        self.argument_parser.add_argument(
            "--verbose",
            help="Increase verbosity",
            action="store_true",
        )

        self.argument_parser.add_argument(
            "-V",
            "--version",
            help="Display version and exit",
            action="store_true",
        )

        subparsers = self.argument_parser.add_subparsers(dest="command")

        self.parsers = {
            "query": subparsers.add_parser("query", help="Query an existing quote"),
            "add": subparsers.add_parser("add", help="Add a new quote"),
            "list": subparsers.add_parser("list", help="List all quotes"),
            "prune": subparsers.add_parser("prune", help="Remove duplicate quotes"),
        }

        self.parsers["query"].add_argument("--author", help="Quote author")
        self.parsers["query"].add_argument("--id", help="Quote ID number")

        self.parsers["add"].add_argument("--author", dest="author", help="Quote author")
        self.parsers["add"].add_argument("--id", help="Quote ID number")
        self.parsers["add"].add_argument("quote", help="The quote text")

        self.parsers["list"].add_argument(
            "--show-duplicates",
            help="List duplicate quotes",
            action="store_true",
        )

    def _parse_args(self) -> argparse.Namespace:
        if len(sys.argv) != 1:
            return self.argument_parser.parse_args()
        else:
            self.argument_parser.print_help()
            sys.exit()


@dataclass
class Quote:

    identifier: int
    quote: str = ""
    author: str = "Anonymous"

    def __str__(self):
        return "Quote #{}: {} - {}".format(self.identifier, self.quote, self.author)


def read_json() -> dict:
    with open("quotes.json", "r") as reader:
        return json.loads(reader.read())


def load_quotes() -> list[Quote]:
    contents = read_json()
    quotes = [Quote(i, contents[i]["quote"], contents[i]["author"]) for i in contents]
    return quotes


def random_quote(quotes: list[Quote]) -> Quote | None:
    if len(quotes):
        return random.choice(quotes)


def add_quote(quote: str, author: str, identifier: int):
    _quote = Quote(identifier, quote, author)

    file_contents = read_json()
    file_contents[_quote.identifier] = {"quote": _quote.quote, "author": _quote.author}

    with open("quotes.json", "w") as writer:
        json.dump(file_contents, writer)
        writer.close()


def list_quotes(quotes: list[Quote], show_duplicates=False):
    seen_quotes = []

    for quote in quotes:
        if quote.quote in seen_quotes:
            if show_duplicates:
                print(quote)
        else:
            print(quote)
        seen_quotes.append(quote.quote)


def get_duplicate_quotes(quotes: list[Quote]) -> list[Quote | None]:
    seen_quotes = []
    duplicates = []

    for quote in quotes:
        if quote.quote in seen_quotes:
            duplicates.append(quote)
        seen_quotes.append(quote.quote)
    return duplicates


def prune_quotes(quotes: dict) -> dict | str:
    l_quotes = load_quotes()
    max_index = len(l_quotes)
    duplicates = get_duplicate_quotes(l_quotes)

    if not len(duplicates):
        return "No duplicates found"
    else:
        for index, duplicate in enumerate(duplicates):
            if isinstance(duplicate, Quote):  # (makes pyright happy)
                del quotes[duplicate.identifier]
    return quotes


def query_quote(
    quotes: list[Quote], identifier=int | None, author=str | None
) -> Optional[Quote]:
    quotes = load_quotes()

    if identifier:
        for quote in quotes:
            if quote.identifier == identifier:
                return quote
    if author:
        selected_quotes = []
        for quote in quotes:
            if quote.author == author:
                selected_quotes.append(quote)
        return random_quote(selected_quotes)


def get_version() -> str:
    # (git must exist for this to work)
    git_path = which("git")

    if git_path is None:
        return "Git is not installed"

    tag = subprocess.run(
        ["git", "describe", "--abbrev=0"],
        encoding="utf8",
        timeout=500.0,
        stdout=subprocess.PIPE,
    )

    if tag.returncode > 0:
        return tag.stderr
    else:
        return tag.stdout


def get_quote_diff(old_list: list[Quote], new_dict) -> int:
    """Find the difference in value between an old and new quote file"""
    diff = len(old_list) - len(new_dict.keys())
    return diff


def main():
    parser = Parser()
    args = parser._parse_args()

    quotes: list[Quote] = load_quotes()

    match args.command:
        case "query":
            quote = query_quote(args.id, args.author)
            if isinstance(quote, Quote):
                print(quote)
            else:
                sys.exit("Couldn't find quote")

        case "add":
            add_quote(args.quote, args.author, len(quotes))
            sys.exit(f"Added quote #{len(quotes)-1}.")

        case "list":
            list_quotes(quotes, args.show_duplicates)

        case "prune":
            refined_quotes = prune_quotes(read_json())
            if isinstance(refined_quotes, dict):
                with open("quotes.json", "w") as writer:
                    json.dump(refined_quotes, writer)
                    writer.close()

                diff = get_quote_diff(quotes, refined_quotes)
                sys.exit(f"Finished pruning quotes. ({diff} duplicates)")
            elif isinstance(refined_quotes, str):
                sys.exit(refined_quotes)
            else:
                raise TypeError("Unexpected type received when pruning quotes")

        case "version":
            sys.exit(get_version())


if __name__ == "__main__":
    main()
