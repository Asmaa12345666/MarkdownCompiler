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
| `*italic text*`     | `<i>italic text</i>`          |
| `` `code` ``        | `<code>code</code>`           |
| `[text](url)`       | `<a href="url">text</a>`      |
| `![alt](url)`       | `<img src="url" alt="alt">`   |
| `---` (alone on a line) | `<hr>`                    |
| `> quote` (consecutive lines grouped) | `<blockquote>…</blockquote>` |
| `- item` (consecutive lines grouped)  | `<ul><li>…</li></ul>`        |
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
python main.py --ll1                   # LL(1) parsing steps (ll1.py)
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
| `ll1.py`       | LL(1) parsing        | Left recursion, left factoring, FIRST/FOLLOW, parse table and stack trace. |
| `input.md`     | —                    | Sample input file. |
| `tests/`       | —                    | One valid file and several files with syntax errors. |

### Tokens (Phase 1)

| Token      | Lexeme                    |
|------------|---------------------------|
| `HASH`     | `#` … `######` at the start of a line |
| `BOLD`     | `**`                      |
| `STAR`     | `*` (italic)              |
| `BACKTICK` | `` ` `` (inline code)     |
| `BANG`     | `!` before `[` (image)    |
| `HR`       | `---` alone on a line     |
| `GT`       | `>` at the start of a line (quote) |
| `DASH`     | `- ` at the start of a line (list item) |
| `LBRACKET` / `RBRACKET` | `[` / `]`    |
| `LPAREN` / `RPAREN`     | `(` / `)`    |
| `TEXT`     | any normal text           |
| `NEWLINE`  | end of line               |
| `EOF`      | end of file               |

Each token stores its type, lexeme, line and column.

### Grammar (Phase 2)

```
Document -> (Block NEWLINE)* Block? EOF
Block    -> HR                  (horizontal rule)
          | HASH Inline+        (heading)
          | GT Inline+          (blockquote line)
          | DASH Inline+        (list item)
          | Inline+             (paragraph)
Inline   -> TEXT
          | BOLD TEXT BOLD
          | STAR TEXT STAR
          | BACKTICK TEXT BACKTICK
          | LBRACKET TEXT RBRACKET LPAREN TEXT RPAREN
          | BANG LBRACKET TEXT? RBRACKET LPAREN TEXT RPAREN
```

### AST nodes

`Document{children}`, `Heading{level, children}`, `Paragraph{children}`,
`Text{value}`, `Bold{value}`, `Italic{value}`, `Code{value}`,
`Link{text, url}`, `Image{alt, url}`, `HorizontalRule`,
`Blockquote{children: [Paragraph]}`, `List{items: [ListItem{children}]}`.

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
| `tests/error_unclosed_italic.md`  | Unclosed italic, missing closing `*` |
| `tests/error_unclosed_code.md`    | Unclosed inline code, missing closing `` ` `` |
| `tests/error_image_missing_rparen.md` | Image is missing closing `)` |
| `tests/error_empty_list_item.md`  | List item cannot be empty |
| `tests/error_empty_blockquote.md` | Blockquote cannot be empty |
| `tests/valid.md`                  | No error, compiles successfully |
| `tests/valid_extensions.md`       | Uses all six extensions |

A missing input file shows `FILE ERROR`.

## LL(1) parsing

`python main.py --ll1` runs `ll1.py`, which builds an LL(1) predictive parser
step by step and prints every step:

1. **Eliminate left recursion**
2. **Left factoring**
3. **FIRST and FOLLOW** sets
4. **Predictive parse table**
5. **Check accept**: a stack / input / output trace for an input string,
   then the **leftmost derivation** taken from the output column

It is run on three grammars:

- The lecture example `E -> E + T | T`, `T -> T * F | F`, `F -> ( E ) | id`
  with the inputs `id+id*id` (accepted) and `id+*id` (rejected).
- A small left-factoring example `S -> a b c | a b d | e`.
- Our own Markdown grammar, using the real tokens of `input.md` from our Lexer.

After removing left recursion the lecture grammar becomes:

```
E  -> T E'
E' -> + T E' | ε
T  -> F T'
T' -> * F T' | ε
F  -> ( E ) | id
```

| Nonterminal | FIRST      | FOLLOW        |
|-------------|------------|---------------|
| E           | { (, id }  | { ), $ }      |
| E'          | { +, ε }   | { ), $ }      |
| T           | { (, id }  | { +, ), $ }   |
| T'          | { *, ε }   | { +, ), $ }   |
| F           | { (, id }  | { +, *, ), $ }|

## Team

| Member | Part |
|--------|------|
| Asmaa  | Lexer (with the new tokens), `main.py`, README, report |
| Omnia  | Parser (with the six extensions), error tests, `ll1.py` |
| Manar  | Code generator |
