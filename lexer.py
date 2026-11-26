"""
Markdown -> HTML Compiler
Phase 1: Lexical Analysis (Scanner)

الـ Lexer بيقرا النص حرف حرف ويقسمه إلى Tokens.
كل Token له:  type (نوعه) + lexeme (النص الحقيقي) + line/col (مكانه)
"""

from dataclasses import dataclass

# ---------------------------------------------------------------
# 1) Token Types
# ---------------------------------------------------------------
HASH     = "HASH"       # #  ##  ###   (في أول السطر فقط)
BOLD     = "BOLD"       # **
LBRACKET = "LBRACKET"   # [
RBRACKET = "RBRACKET"   # ]
LPAREN   = "LPAREN"     # (
RPAREN   = "RPAREN"     # )
TEXT     = "TEXT"       # أي نص عادي
NEWLINE  = "NEWLINE"    # \n
EOF      = "EOF"        # نهاية الملف

# ---- Extensions ----
STAR     = "STAR"       # *        (مائل: *كلام*)
BACKTICK = "BACKTICK"   # `        (كود: `print()`)
HR       = "HR"         # ---      (خط فاصل، لوحده في السطر)
GT       = "GT"         # >        (اقتباس، في أول السطر فقط)
DASH     = "DASH"       # "- "     (عنصر قائمة، في أول السطر فقط)
BANG     = "BANG"       # !        (صورة، لازم بعدها [ على طول)


@dataclass
class Token:
    type: str       # نوع الـ Token
    lexeme: str     # النص الأصلي كما ظهر في الملف
    line: int
    col: int

    def __repr__(self):
        shown = self.lexeme.replace("\n", "\\n")
        return f"Token({self.type:<9} '{shown}'  @ {self.line}:{self.col})"


# ---------------------------------------------------------------
# 2) The Lexer
# ---------------------------------------------------------------
class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.pos = 0        # المؤشر الحالي
        self.line = 1
        self.col = 1

    # ---- دوال مساعدة ----
    def peek(self, offset=0):
        """يشوف الحرف من غير ما يتحرك."""
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else "\0"

    def advance(self):
        """ياخد الحرف الحالي ويحرك المؤشر."""
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def at_end(self):
        return self.pos >= len(self.src)

    def at_line_start(self):
        return self.col == 1

    def is_hr_line(self):
        """السطر كله شرط (---) و3 على الأقل؟ (مسموح مسافات)"""
        end = self.src.find("\n", self.pos)
        rest = self.src[self.pos: end if end != -1 else len(self.src)].strip()
        return len(rest) >= 3 and set(rest) == {"-"}

    # ---- الدالة الرئيسية ----
    def tokenize(self):
        tokens = []

        while not self.at_end():
            line, col = self.line, self.col
            ch = self.peek()

            # 1) سطر جديد
            if ch == "\n":
                self.advance()
                tokens.append(Token(NEWLINE, "\n", line, col))

            # 2) # في أول السطر -> HASH
            elif ch == "#" and self.at_line_start():
                lexeme = ""
                while self.peek() == "#":
                    lexeme += self.advance()
                tokens.append(Token(HASH, lexeme, line, col))

            # 2b) --- لوحده في السطر -> HR
            elif ch == "-" and self.at_line_start() and self.is_hr_line():
                lexeme = ""
                while self.peek() not in ("\n", "\0"):
                    lexeme += self.advance()
                tokens.append(Token(HR, lexeme.strip(), line, col))

            # 2c) "- " في أول السطر -> DASH (عنصر قائمة)
            elif ch == "-" and self.at_line_start() and self.peek(1) == " ":
                self.advance()
                tokens.append(Token(DASH, "-", line, col))

            # 2d) > في أول السطر -> GT (اقتباس)
            elif ch == ">" and self.at_line_start():
                tokens.append(Token(GT, self.advance(), line, col))

            # 3) ** -> BOLD  (حرفين ورا بعض)
            elif ch == "*" and self.peek(1) == "*":
                self.advance()
                self.advance()
                tokens.append(Token(BOLD, "**", line, col))

            # 3b) * لوحدها -> STAR (مائل)
            elif ch == "*":
                tokens.append(Token(STAR, self.advance(), line, col))

            # 3c) ` -> BACKTICK، وجوه الكود بيتقري زي ما هو (raw)
            elif ch == "`":
                tokens.append(Token(BACKTICK, self.advance(), line, col))
                code_line, code_col = self.line, self.col
                code = ""
                while not self.at_end() and self.peek() not in "`\n":
                    code += self.advance()
                if code:
                    tokens.append(Token(TEXT, code, code_line, code_col))
                if self.peek() == "`":
                    tokens.append(Token(BACKTICK, "`", self.line, self.col))
                    self.advance()
                # لو مفيش ` قافلة، الـ Parser هو اللي هيطلع الخطأ

            # 3d) ![ -> BANG (بداية صورة)
            elif ch == "!" and self.peek(1) == "[":
                tokens.append(Token(BANG, self.advance(), line, col))

            # 4) الرموز المفردة
            elif ch == "[":
                tokens.append(Token(LBRACKET, self.advance(), line, col))
            elif ch == "]":
                tokens.append(Token(RBRACKET, self.advance(), line, col))
            elif ch == "(":
                tokens.append(Token(LPAREN, self.advance(), line, col))
            elif ch == ")":
                tokens.append(Token(RPAREN, self.advance(), line, col))

            # 5) غير كده -> TEXT (نكمل لحد أول رمز خاص)
            else:
                lexeme = ""
                while not self.at_end():
                    c = self.peek()
                    if c in "\n[]()*`":
                        break
                    if c == "!" and self.peek(1) == "[":
                        break
                    lexeme += self.advance()
                tokens.append(Token(TEXT, lexeme, line, col))

        tokens.append(Token(EOF, "", self.line, self.col))
        return tokens


# ---------------------------------------------------------------
# 3) Demo
# ---------------------------------------------------------------
import sys

def show(source: str):
    print("-" * 55)
    print(f"{'#':<3}{'TOKEN TYPE':<12}{'LEXEME':<28}{'POSITION'}")
    print("-" * 55)
    for i, t in enumerate(Lexer(source).tokenize(), 1):
        lex = "'" + t.lexeme.replace("\n", "\\n") + "'"
        print(f"{i:<3}{t.type:<12}{lex:<28}{t.line}:{t.col}")


if __name__ == "__main__":
    # اسم الملف ياخده من الأمر، ولو مفيش يستخدم input.md
    filename = sys.argv[1] if len(sys.argv) > 1 else "input.md"
    with open(filename, encoding="utf-8") as f:
        source = f.read()
    print("Reading file:", filename)
    show(source)