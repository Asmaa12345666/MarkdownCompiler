"""
Markdown -> HTML Compiler
main.py: runs the whole compiler

    input.md -> Lexer -> Parser -> Semantic -> Optimizer -> Generator -> index.html

Usage:
    python main.py                      # input.md -> index.html
    python main.py file.md              # file.md  -> index.html
    python main.py file.md out.html     # file.md  -> out.html
    python main.py file.md --tokens     # also print the tokens
    python main.py file.md --ast        # also print the AST (JSON)
    python main.py file.md --tree       # also print the parse tree
    python main.py file.md --prefix     # also print prefix (Polish) notation
    python main.py file.md --derivation # also print the leftmost derivation
    python main.py file.md --report     # also write report.html (tokens, tree, LL(1) ...)
    python main.py file.md --symbols    # also print the Symbol Table (all headings)
    python main.py file.md --optimize   # also print the tree before / after optimization
    python main.py --ll1                # LL(1) part (ll1.py)
    python main.py --help
"""

import argparse
import importlib
import inspect
import json
import os
import sys

from lexer import Lexer
from parser import Parser
from generator import generate, save
from generator import generate_report, ll1_data, to_prefix, leftmost_derivation
from semantic import analyze, show_symbols


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


def optional_module(name):
    """Returns a teammate's module, or None if it is not in the project yet."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        return None


def compile_file(input_file, output_file, show_tokens, show_ast, show_tree,
                 show_prefix=False, show_derivation=False, report_file=None,
                 show_symbols_table=False, show_optimize=False):
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

    if show_prefix:
        print_title("PREFIX (POLISH) NOTATION")
        print(to_prefix(ast))
    if show_derivation:
        print_title("LEFTMOST DERIVATION")
        for rule, form in leftmost_derivation(ast):
            print(f"=> {form}" if rule else form)

    # Phase 3: Semantic Analysis (warnings do not stop the compiler)
    base_dir = os.path.dirname(os.path.abspath(input_file))
    warnings, symbols = analyze(ast, base_dir)
    if show_symbols_table:
        print_title("PHASE 3: SYMBOL TABLE")
        show_symbols(symbols)
    if warnings:
        print_title(f"PHASE 3: SEMANTIC WARNINGS ({len(warnings)})")
        for warning in warnings:
            print(warning)

    # Phase 4: Optimization (Manar's optimizer.py)
    optimizer = optional_module("optimizer")
    if optimizer:
        if show_optimize:
            print_title("PHASE 4: TREE BEFORE OPTIMIZATION")
            print_tree(ast)
        ast, changes = optimizer.optimize(ast)
        if show_optimize:
            print_title("PHASE 4: TREE AFTER OPTIMIZATION")
            print_tree(ast)
            print_title(f"PHASE 4: OPTIMIZATION CHANGES ({len(changes)})")
            print("\n".join(changes) if changes else "Nothing to optimize.")
    elif show_optimize:
        print_title("PHASE 4: OPTIMIZATION")
        print("optimizer.py is not in the project yet (Manar's part).")

    # Phase 5: Code Generation
    if "symbols" in inspect.signature(generate).parameters:
        html_code = generate(ast, symbols=symbols)      # with Table of Contents
    else:
        html_code = generate(ast)
    save(html_code, output_file)

    print_title("COMPILATION SUCCESSFUL")
    print(f"{input_file}  ->  {output_file}")

    # Compiler report (Manar's generate_report + Omnia's LL(1) steps)
    if report_file:
        try:
            ll1 = ll1_data()
        except ImportError:                 # ll1.py not in the folder
            ll1 = None
        save(generate_report(ast, tokens, ll1), report_file)
        print(f"Report      ->  {report_file}")


def main():
    # Show Arabic correctly in the Windows terminal
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    arg_parser = argparse.ArgumentParser(
        description="Markdown to HTML compiler "
                    "(Lexer -> Parser -> Semantic -> Optimizer -> Generator)"
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
    arg_parser.add_argument("--prefix", action="store_true",
                            help="print the prefix (Polish) notation")
    arg_parser.add_argument("--derivation", action="store_true",
                            help="print the leftmost derivation")
    arg_parser.add_argument("--report", action="store_true",
                            help="also write report.html (tokens, tree, prefix, derivation, LL(1))")
    arg_parser.add_argument("--symbols", action="store_true",
                            help="print the Symbol Table (all headings)")
    arg_parser.add_argument("--optimize", action="store_true",
                            help="print the tree before and after optimization")
    arg_parser.add_argument("--ll1", action="store_true",
                            help="run the LL(1) part (ll1.py)")
    args = arg_parser.parse_args()

    if args.ll1:
        print_title("LL(1) PARSING")
        run_optional("ll1", "Omnia")
        return 0

    try:
        compile_file(args.input, args.output,
                     args.tokens, args.ast, args.tree,
                     args.prefix, args.derivation,
                     "report.html" if args.report else None,
                     args.symbols, args.optimize)
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
