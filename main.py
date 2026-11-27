"""
Markdown -> HTML Compiler
main.py: runs the whole compiler

    input.md  ->  Lexer  ->  Tokens  ->  Parser  ->  AST  ->  Generator  ->  index.html

Usage:
    python main.py                      # input.md -> index.html
    python main.py file.md              # file.md  -> index.html
    python main.py file.md out.html     # file.md  -> out.html
    python main.py file.md --tokens     # also print the tokens
    python main.py file.md --ast        # also print the AST (JSON)
    python main.py file.md --tree       # also print the parse tree
    python main.py --ll1                # LL(1) part (ll1.py)
    python main.py --help
"""

import argparse
import importlib
import json
import sys

from lexer import Lexer
from parser import Parser
from generator import generate, save


def read_file(filename):
    with open(filename, encoding="utf-8") as file:
        return file.read()


def print_title(title):
    print()
    print("=" * 50)
    print(title)
    print("=" * 50)


def print_tree(node, prefix="", is_last=True, is_root=True):
    """Draws the AST as a tree, e.g.
    Document
    └── Heading (level 1)
        └── Text: "Hello"
    """
    if is_root:
        print(describe(node))
        new_prefix = ""
    else:
        connector = "└── " if is_last else "├── "
        print(prefix + connector + describe(node))
        new_prefix = prefix + ("    " if is_last else "│   ")

    # List keeps its ListItems in "items", the others use "children"
    children = node.get("children", node.get("items", []))
    for i, child in enumerate(children):
        print_tree(child, new_prefix, i == len(children) - 1, False)


def describe(node):
    kind = node["type"]
    if kind == "Heading":
        return f"Heading (level {node['level']})"
    if kind in ("Text", "Bold", "Italic", "Code"):
        return f'{kind}: "{node["value"]}"'
    if kind == "Link":
        return f'Link: text="{node["text"]}" url="{node["url"]}"'
    if kind == "Image":
        return f'Image: alt="{node["alt"]}" url="{node["url"]}"'
    return kind     # Document, Paragraph, Blockquote, List, ListItem, HorizontalRule


def run_optional(module_name, owner):
    """Runs a teammate's module (ll1.py, ...) if it exists."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"{module_name}.py is not in the project yet ({owner}'s part).")
        return
    module.main()


def compile_file(input_file, output_file, show_tokens, show_ast, show_tree):
    source = read_file(input_file)

    # Phase 1: Lexical Analysis
    tokens = Lexer(source).tokenize()
    if show_tokens:
        print_title("PHASE 1: TOKENS")
        for token in tokens:
            print(token)

    # Phase 2: Syntax Analysis
    ast = Parser(tokens).parse()
    if show_ast:
        print_title("PHASE 2: AST")
        print(json.dumps(ast, indent=4, ensure_ascii=False))
    if show_tree:
        print_title("PHASE 2: PARSE TREE")
        print_tree(ast)

    # Phase 3: Code Generation
    html_code = generate(ast)
    save(html_code, output_file)

    print_title("COMPILATION SUCCESSFUL")
    print(f"{input_file}  ->  {output_file}")


def main():
    # Show Arabic correctly in the Windows terminal
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    arg_parser = argparse.ArgumentParser(
        description="Markdown to HTML compiler (Lexer -> Parser -> Generator)"
    )
    arg_parser.add_argument("input", nargs="?", default="input.md",
                            help="Markdown file (default: input.md)")
    arg_parser.add_argument("output", nargs="?", default="index.html",
                            help="HTML file (default: index.html)")
    arg_parser.add_argument("--tokens", action="store_true",
                            help="print the tokens")
    arg_parser.add_argument("--ast", action="store_true",
                            help="print the AST as JSON")
    arg_parser.add_argument("--tree", action="store_true",
                            help="print the parse tree")
    arg_parser.add_argument("--ll1", action="store_true",
                            help="run the LL(1) part (ll1.py)")
    args = arg_parser.parse_args()

    if args.ll1:
        print_title("LL(1) PARSING")
        run_optional("ll1", "Omnia")
        return 0

    try:
        compile_file(args.input, args.output,
                     args.tokens, args.ast, args.tree)
    except SyntaxError as error:
        print_title("SYNTAX ERROR")
        print(error)
        return 1
    except ValueError as error:
        print_title("GENERATOR ERROR")
        print(error)
        return 1
    except OSError as error:
        print_title("FILE ERROR")
        print(f"Cannot open file: {error.filename}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
