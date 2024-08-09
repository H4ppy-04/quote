#!/usr/bin/env python

"""
A quoting program to be used privately on Linux.
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
import os
import random
import subprocess
import sys
from dataclasses import dataclass
from shutil import which
from typing import override, reveal_type

import selfupdate


def _print(msg, verbose: bool = False):
    if verbose:
        print(msg)


class Parser:

    def __init__(self):
        self.argument_parser = argparse.ArgumentParser()

        _ = self.argument_parser.add_argument(
            "--color",
            choices=["always", "never", "auto"],
            nargs="?",
            help="Color text output",
        )

        _ = self.argument_parser.add_argument(
            "-V",
            "--version",
            help="Display version and exit",
            action="store_true",
        )

        subparsers = self.argument_parser.add_subparsers(dest="command")

        self.parsers = {
            "query": subparsers.add_parser("query", help="Query an existing quote"),
            "add": subparsers.add_parser("add", help="Add a new quote"),
            "prune": subparsers.add_parser("prune", help="Remove duplicate quotes"),
            "update": subparsers.add_parser(
                "update", help="Update to the newest version"
            ),
        }

        _ = self.parsers["query"].add_argument(
            "--author", help="Quote author", required=False
        )
        _ = self.parsers["query"].add_argument(
            "--id", help="Quote ID number", required=False
        )
        _ = self.parsers["query"].add_argument(
            "--list", help="List all quotes", action="store_true"
        )
        _ = self.parsers["query"].add_argument(
            "--show-duplicates",
            help="Show duplicate quotes",
            action="store_true",
        )

        _ = self.parsers["add"].add_argument(
            "--author", dest="author", help="Quote author"
        )
        _ = self.parsers["add"].add_argument("quote", help="The quote text")

        _ = self.parsers["prune"].add_argument(
            "--verbose",
            help="Print deletion events and quote ID's",
            action="store_true",
        )

        _ = self.parsers["update"].add_argument(
            "--verbose",
            help="Print additional messages for debugging",
            action="store_true",
        )
        _ = self.parsers["update"].add_argument(
            "--force",
            help="Ignore any changes made to source code (DESTRUCTIVE)",
            action="store_true",
        )
        _ = self.parsers["update"].add_argument(
            "--check-dev",
            help="Detect and disable destructive actions in a devenv.",
            action="store_true",
        )

        self.args = self._parse_args()

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

    @override
    def __str__(self):
        return "Quote #{}: {} - {}".format(self.identifier, self.quote, self.author)


def read_json(file: str = "quotes.json"):
    with open(file, "r") as reader:
        contents: dict[int, str] = json.loads(reader.read())
        return contents


def load_quotes(file: str = "quotes.json") -> list[Quote]:
    contents: dict = read_json(file)
    quotes: list[Quote] = [
        Quote(i, contents[i]["quote"], contents[i]["author"]) for i in contents
    ]
    return quotes


def random_quote(quotes: list[Quote]) -> Quote | None:
    if len(quotes):
        return random.choice(quotes)


def add_quote(quote: str, author: str, identifier: int, file="quotes.json"):
    _quote = Quote(identifier, quote, author)

    file_contents: dict = read_json(file)
    file_contents[_quote.identifier] = {"quote": _quote.quote, "author": _quote.author}

    with open("quotes.json", "w") as writer:
        json.dump(file_contents, writer)
        writer.close()


def list_quotes(
    quotes: list[Quote], show_duplicates: bool = False, author: str | None = None
) -> list[str]:
    seen_quotes: list[str] = []

    for quote in quotes:
        if author and quote.author != author:
            continue
        if quote.quote in seen_quotes:
            if show_duplicates:
                print(quote)
        else:
            print(quote)
        seen_quotes.append(quote.quote)
    return seen_quotes


def get_duplicate_quotes(quotes: list[Quote]) -> list[Quote] | None:
    seen_quotes: list[str] = []
    duplicates: list[Quote] = []

    for quote in quotes:
        if quote.quote in seen_quotes:
            duplicates.append(quote)
        seen_quotes.append(quote.quote)
    return duplicates


def prune_quotes(quotes_dict: dict[int, str], verbose: bool = False) -> dict | str:
    quotes_list: list[Quote] = load_quotes()
    duplicates: list[Quote] | None = get_duplicate_quotes(quotes_list)

    if (isinstance(duplicates, list) and len(duplicates) == 0) or duplicates is None:
        return "No duplicates found"
    else:
        for index, duplicate in enumerate(duplicates):
            # make sure that the Quote exists (pyright)
            print(f"Checking quote #{index}", verbose)
            if isinstance(duplicate, Quote):
                print(f"Removing quote #{duplicate.identifier}", verbose)
                del quotes_dict[duplicate.identifier]
    return quotes_dict


def query_quote(
    quotes: list[Quote], identifier: int | None, author: str | None
) -> Quote | None:
    if identifier is not None:
        for quote in quotes:
            if int(quote.identifier) == int(identifier):
                return quote
    if author is not None:
        selected_quotes: list[Quote] = []
        for quote in quotes:
            if quote.author == author:
                selected_quotes.append(quote)
        return random_quote(selected_quotes)

    # no identifier or author
    return None


def get_version() -> str:
    """Return most recent tag read from stdout with git"""
    git_path = which("git")

    if git_path is None:
        return "Git is not installed"

    tag = subprocess.run(
        ["git", "describe", "--abbrev=0"],
        encoding="utf8",
        stdout=subprocess.PIPE,
    )

    if tag.returncode > 0:
        return tag.stderr
    else:
        return tag.stdout


def update(
    force: bool = False,
    check_dev: bool = True,
    verbose: bool = False,
):
    cwd = os.getcwd()
    print("Changing CWD to root (/)", verbose)
    print("CWD reverting after call.", verbose)
    os.chdir("/")
    selfupdate.update(force, check_dev, verbose=verbose)
    os.chdir(cwd)


def get_quote_diff(old_list: list[Quote], new_dict: dict[str, Quote]) -> int:
    """Find the difference in value between an old and new quote file"""

    diff = len(old_list) - len(new_dict.keys())
    return diff


def main():
    parser: Parser = Parser()
    quotes: list[Quote] = load_quotes()

    match parser.args.command:
        case "query":
            if parser.args.list:
                _ = list_quotes(
                    quotes,
                    show_duplicates=parser.args.show_duplicates,
                    author=parser.args.author,
                )
            else:
                quote = query_quote(quotes, parser.args.id, author=parser.args.author)
                print(quote)

        case "add":
            add_quote(parser.args.quote, parser.args.author, len(quotes))
            sys.exit(f"Added quote #{len(quotes)-1}.")

        case "prune":
            pruned_quotes: str | dict[str, Quote] = prune_quotes(
                read_json(), parser.args.verbose
            )
            if isinstance(pruned_quotes, dict):
                with open("quotes.json", "w") as writer:
                    json.dump(pruned_quotes, writer)
                    writer.close()

                diff = get_quote_diff(quotes, pruned_quotes)
                sys.exit(f"Finished pruning quotes. ({diff} duplicates)")
            else:
                sys.exit(pruned_quotes)

        case "version":
            sys.exit(get_version())

        case "update":
            update(parser.args.force, parser.args.check_dev, parser.args.verbose)


if __name__ == "__main__":
    main()
