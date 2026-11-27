"""
Markdown -> HTML Compiler
Phase 3: Code Generation

1) generate(ast)            -> the HTML page (index.html)
2) to_prefix(ast)           -> the AST in prefix (Polish) notation
3) leftmost_derivation(ast) -> the steps of the leftmost derivation
4) generate_report(ast, tokens, ll1) -> report.html: tokens, parse tree,
                               prefix notation, derivation (+ LL(1) tables)
"""

import html
import sys


# ======================================================================
# CSS
# ======================================================================
CSS = """
    body {
        font-family: Tahoma, Arial, sans-serif;
        max-width: 800px;
        margin: 40px auto;
        padding: 0 20px;
        line-height: 1.8;
        color: #222;
        background: #fafafa;
    }
    h1, h2, h3, h4, h5, h6 { color: #1a4d8f; }
    a { color: #0b6bcb; }
    b { color: #000; }
    code {
        background: #eee;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: Consolas, monospace;
        direction: ltr;
        unicode-bidi: isolate;
    }
    blockquote {
        margin: 16px 0;
        padding: 4px 16px;
        border-right: 4px solid #1a4d8f;
        background: #eef3fa;
        color: #444;
    }
    hr { border: none; border-top: 2px solid #ccc; margin: 24px 0; }
    img { max-width: 100%; }
"""

# extra CSS used only by report.html
REPORT_CSS = """
    body { max-width: 1000px; }
    section {
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 8px 20px 16px;
        margin-bottom: 24px;
    }
    table { border-collapse: collapse; width: 100%; direction: ltr; }
    th, td { border: 1px solid #ccc; padding: 4px 10px; text-align: left; }
    th { background: #1a4d8f; color: #fff; }
    tr:nth-child(even) td { background: #f4f7fb; }
    pre {
        background: #f4f4f4;
        padding: 12px;
        border-radius: 6px;
        direction: ltr;
        text-align: left;
        white-space: pre-wrap;
        font-family: Consolas, monospace;
    }
    ol.derivation { direction: ltr; text-align: left; font-family: Consolas, monospace; }
"""


# ======================================================================
# 1) HTML page from the AST
# ======================================================================
class Generator:
    # ---------- whole document ----------
    def generate(self, ast):
        body = ""
        for child in ast["children"]:
            body += "    " + self.generate_block(child) + "\n"
        return page("Markdown Compiler", CSS, body)

    # ---------- one block ----------
    def generate_block(self, node):
        kind = node["type"]

        if kind == "Heading":
            level = min(node["level"], 6)          # HTML has h1 .. h6 only
            return f"<h{level}>{self.generate_inline(node['children'])}</h{level}>"

        if kind == "Paragraph":
            return f"<p>{self.generate_inline(node['children'])}</p>"

        if kind == "HorizontalRule":
            return "<hr>"

        if kind == "Blockquote":
            inner = "".join(self.generate_block(child) for child in node["children"])
            return f"<blockquote>{inner}</blockquote>"

        if kind == "List":
            items = "".join(
                f"<li>{self.generate_inline(item['children'])}</li>"
                for item in node["items"]
            )
            return f"<ul>{items}</ul>"

        raise ValueError(f"Unknown node type: {kind}")

    # ---------- inside a line ----------
    def generate_inline(self, children):
        result = ""
        for child in children:
            kind = child["type"]

            if kind == "Text":
                result += html.escape(child["value"])

            elif kind == "Bold":
                result += f"<b>{html.escape(child['value'])}</b>"

            elif kind == "Italic":
                result += f"<i>{html.escape(child['value'])}</i>"

            elif kind == "Code":
                result += f"<code>{html.escape(child['value'])}</code>"

            elif kind == "Link":
                url = html.escape(child["url"], quote=True)
                result += f'<a href="{url}">{html.escape(child["text"])}</a>'

            elif kind == "Image":
                url = html.escape(child["url"], quote=True)
                alt = html.escape(child["alt"], quote=True)
                result += f'<img src="{url}" alt="{alt}">'

            else:
                raise ValueError(f"Unknown node type: {kind}")
        return result


def page(title, css, body):
    """Wraps a body in a full Arabic (right-to-left) HTML page."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ar" dir="rtl">\n'
        "<head>\n"
        '    <meta charset="UTF-8">\n'
        f"    <title>{html.escape(title)}</title>\n"
        "    <style>" + css + "    </style>\n"
        "</head>\n"
        "<body>\n"
        + body +
        "</body>\n"
        "</html>\n"
    )


# ======================================================================
# Helpers to walk the AST
# ======================================================================
def children_of(node):
    """List and Blockquote keep their children under different keys."""
    if node["type"] == "List":
        return node["items"]
    return node.get("children", [])


def label(node):
    """Short name of a node, e.g.  Heading1  or  Text "hello"."""
    kind = node["type"]
    if kind == "Heading":
        return f"Heading{node['level']}"
    if kind in ("Text", "Bold", "Italic", "Code"):
        return f'{kind} "{node["value"]}"'
    if kind == "Link":
        return f'Link "{node["text"]}" "{node["url"]}"'
    if kind == "Image":
        return f'Image "{node["alt"]}" "{node["url"]}"'
    return kind


# ======================================================================
# 2) Prefix (Polish) notation
#    The operator (node) is written BEFORE its operands (children):
#    (Document (Heading1 (Text "Hi")) (Paragraph (Bold "x")))
# ======================================================================
def to_prefix(node):
    kids = children_of(node)
    if not kids:
        return f"({label(node)})"
    inner = " ".join(to_prefix(kid) for kid in kids)
    return f"({label(node)} {inner})"


# ======================================================================
# 3) Leftmost derivation
#
#    Grammar (non-terminals start with a capital letter):
#      Document -> Block Document | ε
#      Block    -> HR | HASH Inlines | GT Inlines | DASH Inlines | Inlines
#      Inlines  -> Inline Inlines | ε
#      Inline   -> TEXT
#                | BOLD TEXT BOLD
#                | STAR TEXT STAR
#                | BACKTICK TEXT BACKTICK
#                | LBRACKET TEXT RBRACKET LPAREN TEXT RPAREN
#                | BANG LBRACKET TEXT RBRACKET LPAREN TEXT RPAREN
#
#    Leftmost derivation = in every step we replace the LEFTMOST
#    non-terminal. That is the same order as a pre-order walk of the tree.
# ======================================================================
NON_TERMINALS = {"Document", "Block", "Inlines", "Inline"}

INLINE_RULES = {
    "Text":   ["TEXT"],
    "Bold":   ["BOLD", "TEXT", "BOLD"],
    "Italic": ["STAR", "TEXT", "STAR"],
    "Code":   ["BACKTICK", "TEXT", "BACKTICK"],
    "Link":   ["LBRACKET", "TEXT", "RBRACKET", "LPAREN", "TEXT", "RPAREN"],
    "Image":  ["BANG", "LBRACKET", "TEXT", "RBRACKET", "LPAREN", "TEXT", "RPAREN"],
}


def source_lines(ast):
    """Turns the AST back into one entry per Markdown line:
    (start_token or None, inline children)."""
    lines = []
    for block in ast["children"]:
        kind = block["type"]
        if kind == "HorizontalRule":
            lines.append(("HR", None))
        elif kind == "Heading":
            lines.append(("HASH", block["children"]))
        elif kind == "Paragraph":
            lines.append((None, block["children"]))
        elif kind == "Blockquote":                 # one GT line per paragraph
            for paragraph in block["children"]:
                lines.append(("GT", paragraph["children"]))
        elif kind == "List":                       # one DASH line per item
            for item in block["items"]:
                lines.append(("DASH", item["children"]))
    return lines


def productions(ast):
    """The productions used, in pre-order (= leftmost) order."""
    rules = []
    for start, inlines in source_lines(ast):
        rules.append(("Document", ["Block", "Document"]))
        if start == "HR":
            rules.append(("Block", ["HR"]))
            continue
        rules.append(("Block", ([start] if start else []) + ["Inlines"]))
        for child in inlines:
            rules.append(("Inlines", ["Inline", "Inlines"]))
            rules.append(("Inline", INLINE_RULES[child["type"]]))
        rules.append(("Inlines", []))              # Inlines -> ε
    rules.append(("Document", []))                 # Document -> ε
    return rules


def leftmost_derivation(ast):
    """Returns a list of steps: (rule used, sentential form after it)."""
    form = ["Document"]
    steps = [("", "Document")]
    for left, right in productions(ast):
        i = next(k for k, sym in enumerate(form) if sym in NON_TERMINALS)
        assert form[i] == left, "derivation out of order"
        form = form[:i] + right + form[i + 1:]
        rule = f"{left} -> {' '.join(right) if right else 'ε'}"
        steps.append((rule, " ".join(form) if form else "ε"))
    return steps


# ======================================================================
# 4) report.html
# ======================================================================
def html_table(headers, rows):
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(
            f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>\n"
    return f"<table>\n<tr>{head}</tr>\n{body}</table>\n"


def tree_text(node, prefix="", is_last=True, is_root=True):
    """Draws the AST like:
    Document
    └── Heading1
        └── Text "Hello"
    """
    if is_root:
        lines = [label(node)]
        new_prefix = ""
    else:
        lines = [prefix + ("└── " if is_last else "├── ") + label(node)]
        new_prefix = prefix + ("    " if is_last else "│   ")
    kids = children_of(node)
    for i, kid in enumerate(kids):
        lines += tree_text(kid, new_prefix, i == len(kids) - 1, False)
    return lines


def ll1_sections(ll1):
    """LL(1) tables in HTML. `ll1` is a dict (all keys optional):
        "grammar": ["E -> T E'", ...]
        "first":   {"E": {"(", "id"}, ...}
        "follow":  {"E": {")", "$"}, ...}
        "table":   {("E", "id"): "E -> T E'", ...}
        "trace":   [("$E", "id+id*id$", "E -> T E'"), ...]
    """
    out = ""
    if "grammar" in ll1:
        out += "<h3>Grammar</h3>\n<pre>" + html.escape("\n".join(ll1["grammar"])) + "</pre>\n"

    if "first" in ll1 or "follow" in ll1:
        first, follow = ll1.get("first", {}), ll1.get("follow", {})
        names = list(dict.fromkeys(list(first) + list(follow)))
        rows = [(n,
                 "{ " + ", ".join(sorted(first.get(n, []))) + " }",
                 "{ " + ", ".join(sorted(follow.get(n, []))) + " }")
                for n in names]
        out += "<h3>FIRST and FOLLOW</h3>\n" + html_table(["Non-terminal", "FIRST", "FOLLOW"], rows)

    if "table" in ll1:
        table = ll1["table"]
        rows_names = list(dict.fromkeys(a for a, _ in table))
        terminals = list(dict.fromkeys(t for _, t in table))
        if "$" in terminals:                       # keep $ as the last column
            terminals = [t for t in terminals if t != "$"] + ["$"]
        rows = [[a] + [table.get((a, t), "") for t in terminals] for a in rows_names]
        out += "<h3>Predictive parsing table</h3>\n" + html_table([""] + terminals, rows)

    if "trace" in ll1:
        out += "<h3>Parsing steps</h3>\n" + html_table(["Stack", "Input", "Output"], ll1["trace"])
    return out


def generate_report(ast, tokens=None, ll1=None, title="Compiler Report"):
    body = f"    <h1>{html.escape(title)}</h1>\n"

    if tokens:
        rows = [(i + 1, t.type, repr(t.lexeme), t.line, t.col) for i, t in enumerate(tokens)]
        body += ("<section><h2>Phase 1: Tokens</h2>\n"
                 + html_table(["#", "Type", "Lexeme", "Line", "Column"], rows)
                 + "</section>\n")

    body += ("<section><h2>Phase 2: Parse tree (AST)</h2>\n<pre>"
             + html.escape("\n".join(tree_text(ast))) + "</pre></section>\n")

    body += ("<section><h2>Prefix (Polish) notation</h2>\n"
             "<p>كل عقدة بتتكتب قبل أولادها (pre-order traversal).</p>\n<pre>"
             + html.escape(to_prefix(ast)) + "</pre></section>\n")

    steps = leftmost_derivation(ast)
    items = "".join(
        f"<li>{'⇒ ' if rule else ''}{html.escape(form)}"
        + (f"   <small>[{html.escape(rule)}]</small>" if rule else "")
        + "</li>\n"
        for rule, form in steps)
    body += ("<section><h2>Leftmost derivation</h2>\n"
             "<p>في كل خطوة بنستبدل أول non-terminal من الشمال.</p>\n"
             f'<ol class="derivation">\n{items}</ol></section>\n')

    if ll1:
        body += "<section><h2>LL(1) parsing</h2>\n" + ll1_sections(ll1) + "</section>\n"

    return page(title, CSS + REPORT_CSS, body)


# ======================================================================
# 5) LL(1) data for the report, taken from Omnia's ll1.py
#    (lecture example: E -> E + T | T ...  checked on id+id*id)
# ======================================================================
LECTURE_GRAMMAR = """
E -> E + T | T
T -> T * F | F
F -> ( E ) | id
"""


def ll1_data(grammar_text=LECTURE_GRAMMAR, text="id+id*id"):
    """Runs the steps of ll1.py and returns them in the shape ll1_sections() wants."""
    import contextlib
    import io
    import ll1

    grammar = ll1.Grammar(grammar_text)
    with contextlib.redirect_stdout(io.StringIO()):     # ll1.py prints its steps; hide them here
        ll1.eliminate_left_recursion(grammar)
        ll1.left_factor(grammar)
    first = ll1.compute_first(grammar)
    follow = ll1.compute_follow(grammar, first)
    table, _ = ll1.build_table(grammar, first, follow)

    def rule(a, p):
        return f"{a} -> {ll1.show_production(p)}"

    # Stack / Input / Output trace (same algorithm as ll1.parse)
    tokens = ll1.split_input(text, grammar.terminals()) + [ll1.END]
    stack, i, trace = [ll1.END, grammar.start], 0, []
    while True:
        top, current = stack[-1], tokens[i]
        row = (" ".join(stack), " ".join(tokens[i:]))
        if top == ll1.END and current == ll1.END:
            trace.append(row + ("ACCEPT",))
            break
        if not grammar.is_nonterminal(top):
            if top != current:
                trace.append(row + (f"ERROR: expected {top}",))
                break
            stack.pop()
            i += 1
            trace.append(row + (f"match {current}",))
            continue
        p = table.get((top, current))
        if p is None:
            trace.append(row + (f"ERROR: M[{top}, {current}] is empty",))
            break
        stack.pop()
        stack.extend(reversed(p))
        trace.append(row + (rule(top, p),))

    return {
        "grammar": [f"{a} -> {' | '.join(ll1.show_production(p) for p in ps)}"
                    for a, ps in grammar.rules.items()],
        "first": first,
        "follow": follow,
        "table": {key: rule(key[0], p) for key, p in table.items()},
        "trace": trace,
    }


# ======================================================================
# Used by main.py
# ======================================================================
def generate(ast):
    """generate(ast) -> HTML string"""
    return Generator().generate(ast)


def save(html_code, filename="index.html"):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_code)


# Quick test: python generator.py input.md
#   writes index.html (the page) and report.html (the compiler report)
if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    if hasattr(sys.stdout, "reconfigure"):          # Arabic in Windows terminal
        sys.stdout.reconfigure(encoding="utf-8")

    filename = sys.argv[1] if len(sys.argv) > 1 else "input.md"

    try:
        with open(filename, encoding="utf-8") as file:
            source = file.read()

        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        save(generate(ast), "index.html")
        try:
            ll1 = ll1_data()
        except ImportError:                            # ll1.py not in the folder
            ll1 = None
        save(generate_report(ast, tokens, ll1), "report.html")

        print("=== PREFIX NOTATION ===")
        print(to_prefix(ast))
        print("\n=== LEFTMOST DERIVATION ===")
        for rule, form in leftmost_derivation(ast):
            print(f"=> {form}" if rule else form)
        print("\nSaved index.html and report.html")

    except (SyntaxError, OSError) as error:
        print("=== COMPILER ERROR ===")
        print(error)
