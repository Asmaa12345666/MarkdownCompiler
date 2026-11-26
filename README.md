# Markdown to HTML Compiler

A small compiler written in Python for our **Compiler Design** course.
It reads a Markdown file and translates it into an HTML web page, going through
the three classic compiler phases: **Lexical Analysis → Syntax Analysis → Code Generation**.

```
input.md ──► Lexer ──► Tokens ──► Parser ──► AST ──► Generator ──► index.html
```

## Supported Markdown

| Markdown            | HTML                          |
|---------------------|-------------------------------|
| `# Title` … `###### Title` | `<h1>` … `<h6>`        |
| `**bold text**`     | `<b>bold text</b>`            |
| `[text](url)`       | `<a href="url">text</a>`      |
| any other line      | `<p>…</p>`                    |

## How to run

You only need **Python 3** (no extra libraries).

```bash
python main.py                         # input.md -> index.html
python main.py file.md                 # file.md  -> index.html
python main.py file.md out.html        # file.md  -> out.html
python main.py file.md --tokens        # also print the tokens (Phase 1)
python main.py file.md --ast           # also print the AST as JSON (Phase 2)
python main.py file.md --tree          # also draw the parse tree (Phase 2)
python main.py --ll1                   # LL(1) parsing part (ll1.py)
python main.py --help
```

Then open `index.html` in any browser.

### Example

`input.md`:

```markdown
# مشروع المترجمات
مرحباً بكم في **جامعتنا**.
يمكنكم زيارة [موقعنا](https://university.edu).
```

`python main.py --tree`:

```
Document
├── Heading (level 1)
│   └── Text: "مشروع المترجمات"
├── Paragraph
│   ├── Text: "مرحباً بكم في "
│   ├── Bold: "جامعتنا"
│   └── Text: "."
└── Paragraph
    ├── Text: "يمكنكم زيارة "
    ├── Link: text="موقعنا" url="https://university.edu"
    └── Text: "."
```

Generated HTML body:

```html
<h1>مشروع المترجمات</h1>
<p>مرحباً بكم في <b>جامعتنا</b>.</p>
<p>يمكنكم زيارة <a href="https://university.edu">موقعنا</a>.</p>
```

## Project structure

| File           | Phase                | What it does |
|----------------|----------------------|--------------|
| `lexer.py`     | 1. Lexical Analysis  | Reads the text character by character and splits it into tokens. |
| `parser.py`    | 2. Syntax Analysis   | Checks the tokens against the grammar and builds the AST. Reports syntax errors. |
| `generator.py` | 3. Code Generation   | Walks the AST and writes a full HTML page (with CSS, right-to-left for Arabic). |
| `main.py`      | Driver               | Runs the three phases in order, handles errors and command-line flags. |
| `input.md`     | —                    | Sample input file. |
| `tests/`       | —                    | One valid file and several files with syntax errors. |

### Tokens (Phase 1)

| Token      | Lexeme                    |
|------------|---------------------------|
| `HASH`     | `#` … `######` at the start of a line |
| `BOLD`     | `**`                      |
| `LBRACKET` / `RBRACKET` | `[` / `]`    |
| `LPAREN` / `RPAREN`     | `(` / `)`    |
| `TEXT`     | any normal text           |
| `NEWLINE`  | end of line               |
| `EOF`      | end of file               |

Each token stores its type, lexeme, line and column.

### Grammar (Phase 2)

```
Document  -> (Line NEWLINE)* Line? EOF
Line      -> Heading | Paragraph
Heading   -> HASH Inline+
Paragraph -> Inline+
Inline    -> TEXT | Bold | Link
Bold      -> BOLD TEXT BOLD
Link      -> LBRACKET TEXT RBRACKET LPAREN TEXT RPAREN
```

### AST nodes

`Document{children}`, `Heading{level, children}`, `Paragraph{children}`,
`Text{value}`, `Bold{value}`, `Link{text, url}`.

## Error handling

The compiler stops at the first error and shows where it happened:

```
python main.py tests/error_unclosed_bold.md

==================================================
SYNTAX ERROR
==================================================
Line 2, column 11: Unclosed bold, missing closing **
```

| Test file                         | Error |
|-----------------------------------|-------|
| `tests/error_unclosed_bold.md`    | Unclosed bold, missing closing `**` |
| `tests/error_missing_rbracket.md` | Link is missing closing `]` |
| `tests/error_missing_rparen.md`   | Link is missing closing `)` |
| `tests/error_empty_url.md`        | Link URL cannot be empty |
| `tests/error_empty_heading.md`    | Heading cannot be empty |
| `tests/valid.md`                  | No error, compiles successfully |

A missing input file shows `FILE ERROR`.

## Team

| Member | Part |
|--------|------|
| Asmaa  | Lexer, `main.py`, README, report |
| Omnia  | Parser, error tests, LL(1) |
| Manar  | Code generator |
