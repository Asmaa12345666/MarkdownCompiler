"""
Markdown -> HTML Compiler
Phase 3: Code Generation
Converts the AST (from the parser) into a full HTML page
"""

import html
import sys


# Simple CSS for the page
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
"""


class Generator:
    # ---------- whole document ----------
    def generate(self, ast):
        body = ""
        for child in ast["children"]:
            body += "    " + self.generate_line(child) + "\n"

        page = (
            "<!DOCTYPE html>\n"
            '<html lang="ar" dir="rtl">\n'
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            "    <title>Markdown Compiler</title>\n"
            "    <style>" + CSS + "    </style>\n"
            "</head>\n"
            "<body>\n"
            + body +
            "</body>\n"
            "</html>\n"
        )
        return page

    # ---------- one line: Heading or Paragraph ----------
    def generate_line(self, node):
        content = self.generate_inline(node["children"])

        if node["type"] == "Heading":
            level = min(node["level"], 6)      # HTML has h1 .. h6 only
            return f"<h{level}>{content}</h{level}>"

        if node["type"] == "Paragraph":
            return f"<p>{content}</p>"

        raise ValueError(f"Unknown node type: {node['type']}")

    # ---------- inside a line: Text, Bold, Link ----------
    def generate_inline(self, children):
        result = ""
        for child in children:
            if child["type"] == "Text":
                result += html.escape(child["value"])

            elif child["type"] == "Bold":
                result += f"<b>{html.escape(child['value'])}</b>"

            elif child["type"] == "Link":
                url = html.escape(child["url"], quote=True)
                text = html.escape(child["text"])
                result += f'<a href="{url}">{text}</a>'

            else:
                raise ValueError(f"Unknown node type: {child['type']}")
        return result


def generate(ast):
    """Shortcut used by main.py: generate(ast) -> HTML string"""
    return Generator().generate(ast)


def save(html_code, filename="index.html"):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_code)


# Quick test: python generator.py input.md
if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    filename = sys.argv[1] if len(sys.argv) > 1 else "input.md"

    try:
        with open(filename, encoding="utf-8") as file:
            source = file.read()

        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        html_code = generate(ast)
        save(html_code, "index.html")

        print("=== GENERATED HTML ===")
        print(html_code)
        print("Saved to index.html")

    except (SyntaxError, OSError) as error:
        print("=== COMPILER ERROR ===")
        print(error)
