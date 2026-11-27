"""
Markdown -> HTML Compiler
LL(1) Predictive Parsing

Steps (each one is printed):
    1) Eliminate left recursion     A -> Aα | β       =>  A -> βA' ,  A' -> αA' | ε
    2) Left factoring               A -> αβ1 | αβ2    =>  A -> αA' ,  A' -> β1 | β2
    3) FIRST and FOLLOW sets
    4) Predictive parse table M[A, a]
    5) Check accept: stack / input / output, then "accepted" or "error"
       + the leftmost derivation (read from the output column)

Run:
    python ll1.py          or          python main.py --ll1
"""

import sys

EPSILON = "ε"
END = "$"


# ---------------------------------------------------------------
# 0) Grammar: read it from text and print it
# ---------------------------------------------------------------
class Grammar:
    def __init__(self, text, start=None):
        """
        text: one rule per line, symbols separated by spaces, ε for empty.
            E -> E + T | T
        """
        self.rules = {}          # {"E": [["E", "+", "T"], ["T"]], ...}
        for line in text.strip().splitlines():
            left, right = line.split("->")
            left = left.strip()
            self.rules[left] = []
            for alternative in right.split("|"):
                symbols = alternative.split()
                if symbols == [EPSILON]:
                    symbols = []         # ε is stored as an empty list
                self.rules[left].append(symbols)
        self.start = start or next(iter(self.rules))

    def nonterminals(self):
        return list(self.rules)

    def is_nonterminal(self, symbol):
        return symbol in self.rules

    def terminals(self):
        found = []
        for productions in self.rules.values():
            for production in productions:
                for symbol in production:
                    if not self.is_nonterminal(symbol) and symbol not in found:
                        found.append(symbol)
        return found

    def new_name(self, name):
        """E -> E' -> E'' ... (a name that is not used yet)"""
        name += "'"
        while name in self.rules:
            name += "'"
        return name

    def insert_after(self, existing, new, productions):
        """Add a new rule right after an existing one (keeps the order nice)."""
        items = list(self.rules.items())
        index = [k for k, _ in items].index(existing)
        items.insert(index + 1, (new, productions))
        self.rules = dict(items)

    def show(self):
        width = max(len(a) for a in self.rules)
        for left, productions in self.rules.items():
            right = " | ".join(show_production(p) for p in productions)
            print(f"    {left:<{width}} → {right}")


def show_production(production):
    return " ".join(production) if production else EPSILON


def title(text):
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


# ---------------------------------------------------------------
# 1) Eliminate left recursion
#    A -> Aα1 | Aα2 | β1 | β2
#    =>  A  -> β1 A' | β2 A'
#        A' -> α1 A' | α2 A' | ε
# ---------------------------------------------------------------
def eliminate_left_recursion(grammar):
    changed = False
    for a in list(grammar.rules):
        recursive = [p[1:] for p in grammar.rules[a] if p and p[0] == a]   # the α's
        others = [p for p in grammar.rules[a] if not p or p[0] != a]        # the β's
        if not recursive:
            continue

        changed = True
        a_dash = grammar.new_name(a)
        print(f"  {a} is left recursive ({a} → {a} ...):")
        grammar.rules[a] = [beta + [a_dash] for beta in others]
        grammar.insert_after(a, a_dash,
                             [alpha + [a_dash] for alpha in recursive] + [[]])
        print(f"    {a} → " + " | ".join(show_production(p) for p in grammar.rules[a]))
        print(f"    {a_dash} → " + " | ".join(show_production(p) for p in grammar.rules[a_dash]))

    if not changed:
        print("  No left recursion.")
    return grammar


# ---------------------------------------------------------------
# 2) Left factoring
#    A -> αβ1 | αβ2 | γ   =>   A -> αA' | γ ,  A' -> β1 | β2
# ---------------------------------------------------------------
def common_prefix(productions):
    prefix = []
    for symbols in zip(*productions):
        if all(s == symbols[0] for s in symbols):
            prefix.append(symbols[0])
        else:
            break
    return prefix


def left_factor(grammar):
    changed = False
    again = True
    while again:                      # repeat until nothing has a common prefix
        again = False
        for a in list(grammar.rules):
            groups = {}               # first symbol -> productions that start with it
            for p in grammar.rules[a]:
                if p:
                    groups.setdefault(p[0], []).append(p)

            for first, group in groups.items():
                if len(group) < 2:
                    continue
                alpha = common_prefix(group)
                a_dash = grammar.new_name(a)
                rest = [p[len(alpha):] for p in group]          # β1, β2 ...

                new_productions = []
                for p in grammar.rules[a]:
                    if p in group:
                        if alpha + [a_dash] not in new_productions:
                            new_productions.append(alpha + [a_dash])
                    else:
                        new_productions.append(p)
                grammar.rules[a] = new_productions
                grammar.insert_after(a, a_dash, rest)

                print(f"  {a}: common prefix '{show_production(alpha)}'")
                print(f"    {a} → " + " | ".join(show_production(p) for p in grammar.rules[a]))
                print(f"    {a_dash} → " + " | ".join(show_production(p) for p in rest))
                changed = again = True
                break
            if again:
                break

    if not changed:
        print("  No common prefixes, nothing to factor.")
    return grammar


# ---------------------------------------------------------------
# 3) FIRST and FOLLOW
# ---------------------------------------------------------------
def first_of_sequence(symbols, first, grammar):
    """FIRST(X1 X2 ... Xn)"""
    result = set()
    for symbol in symbols:
        if not grammar.is_nonterminal(symbol):     # terminal
            result.add(symbol)
            return result
        result |= first[symbol] - {EPSILON}
        if EPSILON not in first[symbol]:
            return result
    result.add(EPSILON)                            # every symbol can be ε (or empty)
    return result


def compute_first(grammar):
    first = {a: set() for a in grammar.rules}
    changed = True
    while changed:                                 # repeat until nothing new is added
        changed = False
        for a, productions in grammar.rules.items():
            for p in productions:
                before = len(first[a])
                first[a] |= first_of_sequence(p, first, grammar)
                if len(first[a]) != before:
                    changed = True
    return first


def compute_follow(grammar, first):
    follow = {a: set() for a in grammar.rules}
    follow[grammar.start].add(END)                 # rule 1: $ in FOLLOW(start)
    changed = True
    while changed:
        changed = False
        for a, productions in grammar.rules.items():
            for p in productions:
                for i, b in enumerate(p):
                    if not grammar.is_nonterminal(b):
                        continue
                    before = len(follow[b])
                    after_b = first_of_sequence(p[i + 1:], first, grammar)
                    follow[b] |= after_b - {EPSILON}   # rule 2: FIRST(β) without ε
                    if EPSILON in after_b:
                        follow[b] |= follow[a]         # rule 3: FOLLOW(A)
                    if len(follow[b]) != before:
                        changed = True
    return follow                                      # ε is never in FOLLOW


def show_set(symbols, order):
    ordered = [s for s in order if s in symbols]
    return "{ " + ", ".join(ordered) + " }"


# ---------------------------------------------------------------
# 4) Predictive parse table
#    for each A -> α:
#       for a in FIRST(α) - {ε}:        M[A, a] = A -> α
#       if ε in FIRST(α):  for b in FOLLOW(A):  M[A, b] = A -> α
# ---------------------------------------------------------------
def build_table(grammar, first, follow):
    table = {}
    conflicts = []
    for a, productions in grammar.rules.items():
        for p in productions:
            first_p = first_of_sequence(p, first, grammar)
            targets = first_p - {EPSILON}
            if EPSILON in first_p:
                targets |= follow[a]
            for t in targets:
                if (a, t) in table and table[(a, t)] != p:
                    conflicts.append((a, t))
                table[(a, t)] = p
    return table, conflicts


def show_table(grammar, table):
    columns = grammar.terminals() + [END]
    cell = {k: f"{k[0]} → {show_production(v)}" for k, v in table.items()}
    # each column is as wide as its longest cell
    width = {c: max([len(cell.get((a, c), "")) for a in grammar.rules] + [len(c)]) + 3
             for c in columns}
    first_width = max(len(a) for a in grammar.rules) + 3

    line = "-" * (first_width + sum(width.values()))
    print(line)
    print(f"{'':<{first_width}}" + "".join(f"{c:<{width[c]}}" for c in columns))
    print(line)
    for a in grammar.rules:
        print(f"{a:<{first_width}}" +
              "".join(f"{cell.get((a, c), ''):<{width[c]}}" for c in columns))
    print(line)


# ---------------------------------------------------------------
# 5) Check accept (table-driven predictive parsing)
# ---------------------------------------------------------------
def split_input(text, terminals):
    """'id+id*id' -> ['id', '+', 'id', '*', 'id']  (longest terminal first)"""
    tokens = []
    text = text.replace(" ", "")
    ordered = sorted(terminals, key=len, reverse=True)
    i = 0
    while i < len(text):
        for t in ordered:
            if text.startswith(t, i):
                tokens.append(t)
                i += len(t)
                break
        else:
            raise SyntaxError(f"Unknown symbol {text[i]!r} at position {i + 1}")
    return tokens


def parse(grammar, table, tokens, show_steps=True):
    """Returns (accepted, list of productions used)."""
    stack = [END, grammar.start]
    tokens = tokens + [END]
    i = 0
    used = []
    rows = []

    while True:
        top = stack[-1]
        current = tokens[i]
        stack_text = " ".join(stack)
        input_text = " ".join(tokens[i:])

        if top == END and current == END:
            rows.append((stack_text, input_text, "ACCEPT"))
            accepted = True
            break

        if not grammar.is_nonterminal(top):              # terminal (or $) on top
            if top == current:
                stack.pop()
                i += 1
                rows.append((stack_text, input_text, f"match {current}"))
                continue
            rows.append((stack_text, input_text,
                         f"ERROR: expected {top}, found {current}"))
            accepted = False
            break

        production = table.get((top, current))
        if production is None:                           # empty cell
            rows.append((stack_text, input_text,
                         f"ERROR: M[{top}, {current}] is empty"))
            accepted = False
            break

        stack.pop()
        stack.extend(reversed(production))               # push right side reversed
        used.append((top, production))
        rows.append((stack_text, input_text, f"{top} → {show_production(production)}"))

    if show_steps:
        w1 = max(len(r[0]) for r in rows + [("STACK", "", "")]) + 3
        w2 = max(len(r[1]) for r in rows + [("", "INPUT", "")]) + 3
        print(f"{'STACK':<{w1}}{'INPUT':>{w2 - 3}}   OUTPUT")
        print("-" * (w1 + w2 + 25))
        for s, inp, out in rows:
            print(f"{s:<{w1}}{inp:>{w2 - 3}}   {out}")

    return accepted, used


def leftmost_derivation(grammar, used):
    """Apply the productions from the output column, always to the leftmost nonterminal."""
    form = [grammar.start]
    steps = [" ".join(form)]
    for left, production in used:
        index = next(k for k, s in enumerate(form) if grammar.is_nonterminal(s))
        form = form[:index] + production + form[index + 1:]
        steps.append(" ".join(form) if form else EPSILON)
    return steps


# ---------------------------------------------------------------
# Run all the steps on one grammar
# ---------------------------------------------------------------
def run(name, grammar_text, inputs, tokenize=None, derivation=False):
    title(f"LL(1): {name}")
    grammar = Grammar(grammar_text)
    print("Original grammar:")
    grammar.show()

    title("Step 1: Eliminate left recursion")
    eliminate_left_recursion(grammar)
    print("\n  Grammar now:")
    grammar.show()

    title("Step 2: Left factoring")
    left_factor(grammar)
    print("\n  Grammar now:")
    grammar.show()

    title("Step 3: FIRST and FOLLOW")
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    order = grammar.terminals() + [EPSILON, END]
    width = max(len(a) for a in grammar.rules)
    for a in grammar.rules:
        print(f"  FIRST({a}){'':<{width - len(a)}} = {show_set(first[a], order)}")
    print()
    for a in grammar.rules:
        print(f"  FOLLOW({a}){'':<{width - len(a)}} = {show_set(follow[a], order)}")

    title("Step 4: Predictive parse table")
    table, conflicts = build_table(grammar, first, follow)
    show_table(grammar, table)
    if conflicts:
        print("  The grammar is NOT LL(1). Conflicts in:",
              ", ".join(f"M[{a}, {t}]" for a, t in conflicts))
        return
    print("  No cell has two productions, so the grammar is LL(1).")

    for text in inputs:
        title(f"Step 5: Check accept for: {text}")
        try:
            tokens = tokenize(text) if tokenize else split_input(text, grammar.terminals())
        except SyntaxError as error:
            print(f"  ERROR: {error}")
            continue
        accepted, used = parse(grammar, table, tokens)
        print()
        print(f"  Result: {'ACCEPTED ✓' if accepted else 'ERROR ✗ (string rejected)'}")

        if accepted and derivation:
            print("\n  Leftmost derivation (from the OUTPUT column):")
            steps = leftmost_derivation(grammar, used)
            print("    " + steps[0])
            for step in steps[1:]:
                print("    ⇒ " + step)


# ---------------------------------------------------------------
# Optional: the same LL(1) on our Markdown grammar
# (the tokens come from our real Lexer)
# ---------------------------------------------------------------
MARKDOWN_GRAMMAR = """
Doc -> Doc Line | ε
Line -> hash Inl nl | Inl nl | nl
Inl -> Inl Item | Item
Item -> text | bold text bold | [ text ] ( text )
"""

TOKEN_TO_TERMINAL = {
    "HASH": "hash", "TEXT": "text", "BOLD": "bold", "NEWLINE": "nl",
    "LBRACKET": "[", "RBRACKET": "]", "LPAREN": "(", "RPAREN": ")",
}


def markdown_tokens(filename):
    from lexer import Lexer
    with open(filename, encoding="utf-8") as file:
        source = file.read()
    if not source.endswith("\n"):
        source += "\n"                       # every line ends with nl in this grammar
    terminals = []
    for token in Lexer(source).tokenize():
        if token.type == "EOF":
            break
        if token.type not in TOKEN_TO_TERMINAL:
            raise SyntaxError(f"Line {token.line}, column {token.col}: "
                              f"{token.type} is not in this small grammar")
        terminals.append(TOKEN_TO_TERMINAL[token.type])
    print(f"  Tokens of {filename}: {' '.join(terminals)}")
    return terminals


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # The example from the lecture
    run("Lecture example",
        """
        E -> E + T | T
        T -> T * F | F
        F -> ( E ) | id
        """,
        inputs=["id+id*id", "id+*id"],
        derivation=True)

    # A small example only to show left factoring
    title("Extra: left factoring example")
    g = Grammar("S -> a b c | a b d | e")
    print("Original grammar:")
    g.show()
    print()
    left_factor(g)
    print("\n  Grammar now:")
    g.show()

    # Our Markdown grammar
    run("Markdown grammar (input.md)",
        MARKDOWN_GRAMMAR,
        inputs=["input.md"],
        tokenize=markdown_tokens,
        derivation=True)


if __name__ == "__main__":
    main()
