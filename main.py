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
import sys
from dataclasses import dataclass, field


# Is there a better way to do forward function declarations?? - Josh
def new_quote_id() -> int: ...


@dataclass
class Quote:

    identifier: int = field(default_factory=new_quote_id(), init=True)
    quote: str = ""
    author: str = "Anonymous"


def read_json():
    with open("quotes.json", "r") as reader:
        return json.loads(reader.read())


def load_quotes() -> list[Quote]:
    contents = read_json()
    return [Quote(i, contents[i]["quote"], contents[i]["author"]) for i in contents]


def random_quote(quotes: list[Quote]) -> Quote:
    return random.choice(quotes)


def new_quote_id() -> int:
    return len(load_quotes())


def add_quote(quote: str, author: str):
    quote = Quote(len(load_quotes()), quote, author)
    quote_json = {str(quote.identifier): {"quote": quote.quote, "author": quote.author}}

    file_contents = {}

    with open("quotes.json", "r") as reader:
        file_contents = json.loads(reader.read())
        reader.close()

    file_contents[quote.identifier] = {"quote": quote.quote, "author": quote.author}

    with open("quotes.json", "w") as writer:
        json.dump(file_contents, writer)
        writer.close()


def parse():
    parser = argparse.ArgumentParser(description="For all your quoting needs...")
    subparsers = parser.add_subparsers(dest="subparser")

    add_parser = subparsers.add_parser("add", help="Add a quote to existing quotes")
    add_parser.add_argument(
        "--author", dest="author", default="Anon", help="Quote author"
    )
    add_parser.add_argument("quote", help="The quote text")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    args = parser.parse_args()
    return args


def main():
    args = parse()
    quotes = load_quotes()

    if args.quote:
        print(f"Added quote as #{len(quotes)}.\n")
        add_quote(args.quote, args.author)


if __name__ == "__main__":
    main()
