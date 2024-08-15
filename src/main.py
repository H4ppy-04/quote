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
from typing import override

import update
from update import __print as _print

# the default quote file that is presumed to be present in ../ relative to main.py
QUOTE_FILE: str = "quotes.json"


class Parser:

    def __init__(self):
        self.argument_parser = argparse.ArgumentParser()

        self.argument_parser.add_argument(
            "-V",
            "--version",
            help="Display version and exit",
            action="store_true",
        )

        self.argument_parser.add_argument(
            "--verbose",
            help="Display additional log messages",
            action="store_true",
            default=False,
        )

        self.argument_parser.add_argument(
            "--file",
            help=f"Use a custom quotes file instead of the default {QUOTE_FILE} file",
            required=False,
            type=str,
        )

        self.argument_parser.add_argument(
            "qotd",
            help="Get the quote of the day!",
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

        query_group = self.parsers["query"].add_mutually_exclusive_group(required=True)

        query_group.add_argument("--author", help="Quote author")
        query_group.add_argument("--id", help="Quote ID number")

        query_group.add_argument("--list", help="List all quotes", action="store_true")
        query_group.add_argument(
            "--show-duplicates",
            help="Show duplicate quotes",
            action="store_true",
        )

        self.parsers["add"].add_argument("--author", dest="author", help="Quote author")
        self.parsers["add"].add_argument("quote", help="The quote text")

        self.parsers["update"].add_argument(
            "--force",
            help="Ignore any changes made to source code (DESTRUCTIVE)",
            action="store_true",
        )
        self.parsers["update"].add_argument(
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


def file_is_empty(file=QUOTE_FILE) -> bool:
    return os.stat(file).st_size == 0


def read_json(file=QUOTE_FILE):
    if not os.path.exists(file):
        with open(file, "w") as fs:
            fs.close()
    elif not file_is_empty(file):
        with open(file, "r") as reader:
            contents: dict[int, str] = json.loads(reader.read())
            return contents
    return json.loads("{}")


def load_quotes(file=QUOTE_FILE) -> list[Quote]:
    contents: dict = read_json(file)
    quotes: list[Quote] = [
        Quote(i, contents[i]["quote"], contents[i]["author"]) for i in contents
    ]
    return quotes


def random_quote(quotes: list[Quote]) -> Quote | None:
    if len(quotes):
        return random.choice(quotes)


def add_quote(quote: str, author: str, identifier: int, file=QUOTE_FILE):
    _quote = Quote(identifier, quote, author)

    file_contents: dict = read_json(file)
    file_contents[_quote.identifier] = {"quote": _quote.quote, "author": _quote.author}

    with open(QUOTE_FILE, "w") as writer:
        json.dump(file_contents, writer)
        writer.close()


def list_quotes(
    quotes: list[Quote],
    show_duplicate_quotes: bool = False,
    author_filter: str | None = None,
) -> list[str]:
    seen_quotes: list[str] = []

    for quote in quotes:
        if author_filter and quote.author != author_filter:
            continue
        if quote.quote in seen_quotes and show_duplicate_quotes:
            print(quote)
        seen_quotes.append(quote.quote)
    return seen_quotes


def get_duplicate_quotes(quotes: list[Quote]) -> list[Quote] | None:
    seen_quotes: list[str] = []
    duplicate_quotes: list[Quote] = []

    for quote in quotes:
        if quote.quote in seen_quotes:
            duplicate_quotes.append(quote)
        seen_quotes.append(quote.quote)
    return duplicate_quotes


def write_pruned_quotes(
    quotes_list: list[Quote], quotes_dict: dict, verbose: bool = False, file=QUOTE_FILE
):

    with open(file, "w") as writer:
        json.dump(quotes_dict, writer)
        writer.close()

    quote_difference = get_quote_diff(quotes_list, quotes_dict)
    _print(
        verbose,
        f"Finished pruning quotes. ({quote_difference} duplicates)",
    )


def read_pruned_quotes(
    quotes_dict: dict[int, str], verbose: bool = False
) -> dict | str:
    quotes_list: list[Quote] = load_quotes()
    duplicate_quotes: list[Quote] | None = get_duplicate_quotes(quotes_list)

    if (
        isinstance(duplicate_quotes, list) and len(duplicate_quotes) == 0
    ) or duplicate_quotes is None:
        return "No duplicates found"

    for index, duplicate in enumerate(duplicate_quotes):
        _print(verbose, f"Removing quote #{duplicate.identifier}")
        del quotes_dict[duplicate.identifier]
    return quotes_dict


def query_quote(
    quotes: list[Quote], quote_identifier: int | None, quote_author: str | None
) -> Quote | None:
    if quote_identifier is not None:
        for quote in quotes:
            if int(quote.identifier) == int(quote_identifier):
                return quote
    if quote_author is not None:
        selected_quotes: list[Quote] = []
        for quote in quotes:
            if quote.author == quote_author:
                selected_quotes.append(quote)
        return random_quote(selected_quotes)

    # no identifier or author
    return None


def get_version() -> str:
    """Return most recent tag read from stdout with git"""
    git_path = which("git")

    if git_path is None:
        return "Git is not installed"

    tag_process = subprocess.run(
        ["git", "describe", "--abbrev=0"],
        encoding="utf8",
        stdout=subprocess.PIPE,
    )

    if tag_process.returncode > 0:
        return tag_process.stderr
    else:
        return tag_process.stdout


def update_changes(
    force: bool = False,
    check_dev: bool = True,
    verbose: bool = False,
):
    initial_working_directory = os.getcwd()
    _print(verbose, "Changing CWD to root (/)\nReverting after call.")
    os.chdir("/")
    update.pull_changes(force, check_dev, verbose=verbose)
    os.chdir(initial_working_directory)


def get_quote_diff(old_list: list[Quote], new_dict: dict[str, Quote]) -> int:
    """Find the difference in value between an old and new quote file"""

    quote_difference = len(old_list) - len(new_dict.keys())
    return quote_difference


def main():
    parser: Parser = Parser()
    quotes: list[Quote] = load_quotes()
    quote_file = parser.args.file if parser.args.file is not None else QUOTE_FILE

    match parser.args.command:
        case "qotd":
            quote = random_quote(quotes)
            if quote is not None:
                print(quote)
            else:
                _print(parser.args.verbose, "Couldn't find any quotes! :'(")

        case "query":
            if parser.args.list:
                list_quotes(
                    quotes,
                    show_duplicate_quotes=parser.args.show_duplicates,
                    author_filter=parser.args.author,
                )
            else:
                quote = query_quote(quotes, parser.args.id, parser.args.author)
                print(quote)

        case "add":
            add_quote(
                parser.args.quote, parser.args.author, len(quotes), file=quote_file
            )
            _print(parser.args.verbose, f"Added quote #{len(quotes)-1}.")

        case "prune":
            pruned_quotes: str | dict[str, Quote] = read_pruned_quotes(
                read_json(file=quote_file), parser.args.verbose
            )
            quotes_is_dict = isinstance(pruned_quotes, dict)
            if quotes_is_dict:
                write_pruned_quotes(quotes, pruned_quotes, parser.args.verbose)
            elif quotes_is_dict is False:
                _print(parser.args.verbose, pruned_quotes)

        case "version":
            current_version = get_version()
            print(current_version)

        case "update":
            update_changes(
                parser.args.force, parser.args.check_dev, parser.args.verbose
            )


sys.exit()


if __name__ == "__main__":
    main()
