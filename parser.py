"""
Markdown -> HTML Compiler
Phase 2: Syntax Analysis (Parser)
Builds an Abstract Syntax Tree (AST)
"""

from lexer import Lexer, EOF, NEWLINE, HASH, BOLD
from lexer import TEXT, LBRACKET, RBRACKET, LPAREN, RPAREN
from lexer import STAR, BACKTICK, HR, GT, DASH, BANG
import json
import sys


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.last_block_was_adjacent = False   # used to group list / quote lines

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

    def error(self, token, message):
        raise SyntaxError(f"Line {token.line}, column {token.col}: {message}")

    # DOCUMENT -> (BLOCK NEWLINE)* BLOCK? EOF
    def parse(self):
        document = {
            "type": "Document",
            "children": []
        }

        while self.current().type != EOF:
            if self.current().type == NEWLINE:
                self.advance()
                continue

            block = self.parse_block()

            # consecutive "- item" lines -> one List
            # consecutive "> quote" lines -> one Blockquote
            previous = document["children"][-1] if document["children"] else None
            if (previous and previous["type"] == block["type"]
                    and block["type"] in ("List", "Blockquote")
                    and self.last_block_was_adjacent):
                key = "items" if block["type"] == "List" else "children"
                previous[key].extend(block[key])
            else:
                document["children"].append(block)

            self.end_of_line()

        self.expect(EOF)
        return document

    def end_of_line(self):
        """After a block: NEWLINE or EOF. Remembers if the next line follows directly."""
        if self.current().type == NEWLINE:
            self.advance()
            # a blank line ends a list / blockquote
            self.last_block_was_adjacent = self.current().type != NEWLINE
        elif self.current().type != EOF:
            self.error(self.current(), "Expected NEWLINE or EOF")

    # BLOCK -> HR | HASH INLINE* | GT INLINE* | DASH INLINE+ | INLINE+
    def parse_block(self):
        start = self.current()   # first token of the line (for error positions)

        if start.type == HR:
            self.advance()
            return {"type": "HorizontalRule"}

        if start.type == HASH:
            level = len(self.advance().lexeme)   # "#" -> 1, "##" -> 2 ...
            children = self.parse_inlines()
            if not children:
                self.error(start, "Heading cannot be empty")
            return {"type": "Heading", "level": level, "children": children}

        if start.type == GT:
            self.advance()
            children = self.parse_inlines()
            if not children:
                self.error(start, "Blockquote cannot be empty")
            return {"type": "Blockquote",
                    "children": [{"type": "Paragraph", "children": children}]}

        if start.type == DASH:
            self.advance()
            children = self.parse_inlines()
            if not children:
                self.error(start, "List item cannot be empty")
            return {"type": "List",
                    "items": [{"type": "ListItem", "children": children}]}

        children = self.parse_inlines(strip=False)
        return {"type": "Paragraph", "children": children}

    # INLINE* until end of line
    def parse_inlines(self, strip=True):
        children = []
        while self.current().type not in (NEWLINE, EOF):
            children.append(self.parse_inline())

        if strip and children and children[0]["type"] == "Text":
            # "# Title" / "> quote" / "- item" -> remove the space after the marker
            children[0]["value"] = children[0]["value"].lstrip()
            if not children[0]["value"]:
                children.pop(0)          # it was only spaces
        return children

    # INLINE -> TEXT | BOLD TEXT BOLD | STAR TEXT STAR | BACKTICK TEXT? BACKTICK
    #         | LBRACKET TEXT RBRACKET LPAREN TEXT RPAREN
    #         | BANG LBRACKET TEXT? RBRACKET LPAREN TEXT RPAREN
    def parse_inline(self):
        token = self.current()

        if token.type == TEXT:
            self.advance()
            return {"type": "Text", "value": token.lexeme}

        if token.type == BOLD:
            return {"type": "Bold",
                    "value": self.parse_wrapped(BOLD, "bold", "**")}

        if token.type == STAR:
            return {"type": "Italic",
                    "value": self.parse_wrapped(STAR, "italic", "*")}

        if token.type == BACKTICK:
            self.advance()
            code = ""
            if self.current().type == TEXT:
                code = self.advance().lexeme
            if self.current().type != BACKTICK:
                self.error(token, "Unclosed inline code, missing closing `")
            self.advance()
            return {"type": "Code", "value": code}

        if token.type == LBRACKET:
            text, url = self.parse_link_parts(token, "Link", allow_empty_text=False)
            return {"type": "Link", "text": text, "url": url}

        if token.type == BANG:
            self.advance()
            if self.current().type != LBRACKET:
                self.error(token, "Expected [ after ! in image")
            alt, url = self.parse_link_parts(token, "Image", allow_empty_text=True)
            return {"type": "Image", "alt": alt, "url": url}

        self.error(token, f"Unexpected token {token.type}")

    def parse_wrapped(self, marker, name, symbol):
        """BOLD TEXT BOLD  or  STAR TEXT STAR"""
        token = self.advance()
        if self.current().type != TEXT:
            self.error(token, f"Expected text inside {name} markers")
        value = self.advance().lexeme
        if self.current().type != marker:
            self.error(token, f"Unclosed {name}, missing closing {symbol}")
        self.advance()
        return value

    def parse_link_parts(self, token, name, allow_empty_text):
        """[text](url)  -> (text, url).  token = first token (for errors)"""
        self.expect(LBRACKET)

        text = ""
        if allow_empty_text and self.current().type == RBRACKET:
            pass                                 # ![](pic.png) -> empty alt
        else:
            text = self.expect(TEXT).lexeme

        if self.current().type != RBRACKET:
            self.error(token, f"{name} is missing closing ]")
        self.advance()
        self.expect(LPAREN)

        # [text]() -> empty URL
        url = ""
        if self.current().type == TEXT:
            url = self.advance().lexeme

        if self.current().type != RPAREN:
            self.error(token, f"{name} is missing closing )")
        self.advance()

        if not url.strip():
            self.error(token, f"{name} URL cannot be empty")

        return text.strip(), url.strip()


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