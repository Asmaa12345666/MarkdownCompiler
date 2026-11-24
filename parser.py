
"""
Markdown -> HTML Compiler
Phase 2: Syntax Analysis (Parser)
Builds an Abstract Syntax Tree (AST)
"""

from lexer import Lexer, EOF, NEWLINE, HASH, BOLD
from lexer import TEXT, LBRACKET, RBRACKET, LPAREN, RPAREN
import json
import sys


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        token = self.current()
        if token.type != EOF:
            self.pos += 1
        return token

    def expect(self, expected_type):
        token = self.current()

        if token.type != expected_type:
            raise SyntaxError(
                f"Line {token.line}, column {token.col}: "
                f"Expected {expected_type}, "
                f"but found {token.type} ({token.lexeme!r})"
            )

        self.advance()
        return token

    # DOCUMENT -> (LINE NEWLINE)* LINE? EOF
    def parse(self):
        document = {
            "type": "Document",
            "children": []
        }

        while self.current().type != EOF:
            if self.current().type == NEWLINE:
                self.advance()
                continue

            document["children"].append(self.parse_line())

            if self.current().type == NEWLINE:
                self.advance()
            elif self.current().type != EOF:
                token = self.current()
                raise SyntaxError(
                    f"Line {token.line}, column {token.col}: "
                    "Expected NEWLINE or EOF"
                )

        self.expect(EOF)
        return document

    # LINE -> HASH INLINE* | INLINE+
    def parse_line(self):
        if self.current().type == HASH:
            self.advance()
            line_type = "Heading"
        else:
            line_type = "Paragraph"

        children = []

        while self.current().type not in (NEWLINE, EOF):
            token = self.current()

            if token.type == TEXT:
                self.advance()
                children.append({
                    "type": "Text",
                    "value": token.lexeme
                })

            elif token.type == BOLD:
                self.advance()

                if self.current().type != TEXT:
                    raise SyntaxError(
                        f"Line {token.line}, column {token.col}: "
                        "Expected text inside bold markers"
                    )

                bold_text = self.advance().lexeme
                self.expect(BOLD)

                children.append({
                    "type": "Bold",
                    "value": bold_text
                })

            elif token.type == LBRACKET:
                self.advance()

                link_text = self.expect(TEXT).lexeme
                self.expect(RBRACKET)
                self.expect(LPAREN)
                url = self.expect(TEXT).lexeme
                self.expect(RPAREN)

                if not url.strip():
                    raise SyntaxError("Link URL cannot be empty")

                children.append({
                    "type": "Link",
                    "text": link_text,
                    "url": url
                })

            else:
                raise SyntaxError(
                    f"Line {token.line}, column {token.col}: "
                    f"Unexpected token {token.type}"
                )

        if line_type == "Heading" and not children:
            raise SyntaxError("Heading cannot be empty")

        return {
            "type": line_type,
            "children": children
        }


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else "input.md"

    try:
        with open(filename, encoding="utf-8") as file:
            source = file.read()

        # Phase 1: Lexical Analysis
        tokens = Lexer(source).tokenize()

        print("=== TOKENS ===")
        for token in tokens:
            print(token)

        # Phase 2: Syntax Analysis
        parser = Parser(tokens)
        ast = parser.parse()

        print("\n=== PARSING SUCCESSFUL ===")
        print("=== ABSTRACT SYNTAX TREE (AST) ===")
        print(json.dumps(ast, indent=4, ensure_ascii=False))

    except (SyntaxError, OSError) as error:
        print("\n=== COMPILER ERROR ===")
        print(error)


if __name__ == "__main__":
    main()
