"""
Markdown -> HTML Compiler
Phase 3: Semantic Analysis + Symbol Table

The parser only checks the FORM of the text (syntax).
Here we check the MEANING: things that are written correctly but are
probably mistakes. They are WARNINGS, so compilation continues.

    analyze(ast, base_dir=".") -> (warnings, symbols)

warnings : list of strings  "Line N: Warning: ..."
symbols  : the Symbol Table, one entry for every heading
           {"name": "...", "level": 1, "line": 3, "id": "section-1"}

It also adds "id" to every Heading node (used for the Table of Contents).
"""

import os

SAFE_URL_STARTS = ("http://", "https://", "mailto:", "#")


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def children_of(node):
    """List keeps its ListItems in "items", the others use "children"."""
    if node["type"] == "List":
        return node.get("items", [])
    return node.get("children", [])


def plain_text(nodes):
    """The text of inline nodes without any formatting: [Bold "Hi"] -> "Hi"."""
    text = ""
    for node in nodes:
        if node["type"] in ("Text", "Bold", "Italic", "Code"):
            text += node["value"]
        elif node["type"] == "Link":
            text += node["text"]
        elif node["type"] == "Image":
            text += node["alt"]
    return text.strip()


def walk(node, line=None):
    """Visits every node (pre-order). Inline nodes take the line of their block."""
    line = node.get("line", line)
    yield node, line
    for child in children_of(node):
        yield from walk(child, line)


class SemanticAnalyzer:
    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.warnings = []
        self.symbols = []           # the Symbol Table

    def warn(self, line, message):
        where = f"Line {line}: " if line else ""
        self.warnings.append(f"{where}Warning: {message}")

    # -----------------------------------------------------------
    # Pass 1: build the Symbol Table (all headings)
    # -----------------------------------------------------------
    def collect_headings(self, ast):
        previous_level = 0
        seen = {}                   # name -> line of first use

        for node, line in walk(ast):
            if node["type"] != "Heading":
                continue

            name = plain_text(node["children"])
            level = node["level"]
            node["id"] = f"section-{len(self.symbols) + 1}"

            # Rule 1: heading levels should not jump (# then ###)
            if level > previous_level + 1:
                if previous_level == 0:
                    self.warn(line, f'first heading "{name}" is level {level}, '
                                    f"it should start at level 1 (#)")
                else:
                    self.warn(line, f'heading "{name}" jumps from level '
                                    f"{previous_level} to level {level}")
            previous_level = level

            # Rule 2: two headings with the same name
            if name in seen:
                where = f" (first used on line {seen[name]})" if seen[name] else ""
                self.warn(line, f'duplicate heading "{name}"{where}')
            else:
                seen[name] = line

            self.symbols.append({"name": name, "level": level,
                                 "line": line, "id": node["id"]})

    # -----------------------------------------------------------
    # Pass 2: check links and images (uses the Symbol Table)
    # -----------------------------------------------------------
    def check_references(self, ast):
        ids = {symbol["id"] for symbol in self.symbols}

        for node, line in walk(ast):
            if node["type"] == "Link":
                url = node["url"]
                # Rule 3: link to a section that does not exist
                #         (like using an undeclared variable)
                if url.startswith("#") and url[1:] not in ids:
                    self.warn(line, f'link "{node["text"]}" points to {url}, '
                                    "but there is no section with this id")
                # Rule 4: url that does not look like an address
                elif not url.startswith(SAFE_URL_STARTS) and "." not in url:
                    self.warn(line, f'link "{node["text"]}" has a strange url '
                                    f'"{url}" (missing https:// ?)')

            elif node["type"] == "Image":
                url = node["url"]
                # Rule 5: image file not found
                if not url.startswith(("http://", "https://")):
                    if not os.path.exists(os.path.join(self.base_dir, url)):
                        self.warn(line, f'image file "{url}" not found')
                # Rule 6: image without description (accessibility)
                if not node["alt"].strip():
                    self.warn(line, f'image "{url}" has no alt text')

    def analyze(self, ast):
        self.collect_headings(ast)
        self.check_references(ast)
        return self.warnings, self.symbols


def analyze(ast, base_dir="."):
    """Used by main.py: analyze(ast) -> (warnings, symbols)"""
    return SemanticAnalyzer(base_dir).analyze(ast)


def show_symbols(symbols):
    """Prints the Symbol Table as a table."""
    print(f"{'#':<4}{'ID':<13}{'LEVEL':<7}{'LINE':<6}NAME")
    print("-" * 50)
    for i, s in enumerate(symbols, 1):
        line = s["line"] if s["line"] else "-"
        print(f"{i:<4}{s['id']:<13}{s['level']:<7}{line!s:<6}{'  ' * (s['level'] - 1)}{s['name']}")


# Quick test: python semantic.py file.md
if __name__ == "__main__":
    import sys
    from lexer import Lexer
    from parser import Parser

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    filename = sys.argv[1] if len(sys.argv) > 1 else "input.md"
    with open(filename, encoding="utf-8") as file:
        tree = Parser(Lexer(file.read()).tokenize()).parse()

    found, table = analyze(tree, os.path.dirname(os.path.abspath(filename)))
    print("=== SYMBOL TABLE ===")
    show_symbols(table)
    print("\n=== WARNINGS ===")
    print("\n".join(found) if found else "No warnings.")
