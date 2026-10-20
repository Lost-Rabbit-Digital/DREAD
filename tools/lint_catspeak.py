#!/usr/bin/env python3
"""
Static checker for Zero Sievert Catspeak (Katspeak 3.1.1) mod scripts.

Catches the class of bug that crashed DREAD on load: Catspeak 3.1.1 functions
are NOT closures. When the compiler resolves an identifier inside a `func`, it
only searches the blocks of *that* function (see `createGet` in
scr_catspeak_ir.gml). Anything else compiles to a lookup on the file's dynamic
globals struct. A top-level `let X = ...` lives in a local slot of the
top-level function, so every reference to X from inside a `func` reads
`undefined` at runtime -> "value is not a function, got 'undefined'".

Checks:
  E001  identifier used inside a func refers to a top-level `let` (undefined at runtime)
  E002  call to a name that is neither exposed by the game, a mod global, nor a local
  E003  obj_* identifier that the game does not expose
  W001  `self.` used inside a func (self is the GML instance / file globals, not the struct)
  W002  name used before the top-level statement that assigns it

Usage: python -I tools/lint_catspeak.py <script> [--exposed docs/api/exposed_values.txt]
Exit code 1 if any E-level issue is found.
"""
import argparse
import re
import sys
from pathlib import Path

KEYWORDS = {
    "let", "func", "fun", "if", "else", "while", "match", "case", "return",
    "break", "continue", "and", "or", "not", "true", "false", "undefined",
    "self", "other", "with", "do", "catch", "params", "new", "throw",
    "infinity", "NaN",
}

TOKEN_RE = re.compile(
    r'(?P<ws>\s+)'
    r'|(?P<comment>--[^\n]*)'
    r'|(?P<str>"(?:\\.|[^"\\])*")'
    r'|(?P<num>\d+(?:\.\d+)?)'
    r'|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<op>==|!=|<=|>=|\+=|-=|\*=|/=|//|[{}()\[\].,:;=<>+\-*/!%&|^~#?@$])'
)


def tokenize(src):
    line = 1
    pos = 0
    out = []
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise SyntaxError(f"line {line}: cannot tokenize near {src[pos:pos+20]!r}")
        kind = m.lastgroup
        text = m.group(kind)
        if kind not in ("ws", "comment"):
            out.append((kind, text, line))
        line += text.count("\n")
        pos = m.end()
    return out


class Scope:
    def __init__(self, is_func, start_depth):
        self.is_func = is_func
        self.names = set()
        self.start_depth = start_depth  # brace depth at which this scope's body opened


def lint(path, exposed):
    src = Path(path).read_text(encoding="utf-8")
    toks = tokenize(src)
    issues = []

    # Pass 1: top-level `let` names and top-level dynamic globals (NAME = ...).
    toplevel_lets, toplevel_globals = {}, {}
    depth = 0
    for i, (k, t, ln) in enumerate(toks):
        if t in "{([":
            depth += 1
        elif t in "})]":
            depth -= 1
        elif depth == 0 and k == "ident":
            prev = toks[i - 1][1] if i else ";"
            nxt = toks[i + 1][1] if i + 1 < len(toks) else ""
            if prev == "let":
                toplevel_lets.setdefault(t, ln)
            elif nxt == "=" and prev in (";", "}", ")") or (nxt == "=" and i == 0):
                toplevel_globals.setdefault(t, ln)

    # Pass 2: walk with a scope stack.
    stack = [Scope(True, 0)]  # top-level function
    depth = 0
    pending_func = None  # collecting params for a func
    i = 0
    while i < len(toks):
        k, t, ln = toks[i]
        prev = toks[i - 1][1] if i else ""
        nxt = toks[i + 1][1] if i + 1 < len(toks) else ""

        if k == "ident" and t in ("func", "fun") and nxt == "(":
            # collect params
            j = i + 2
            params = set()
            while toks[j][1] != ")":
                if toks[j][0] == "ident":
                    params.add(toks[j][1])
                j += 1
            # toks[j] == ")", next should be "{"
            pending_func = params
            i = j + 1
            continue

        if t == "{":
            depth += 1
            if pending_func is not None:
                s = Scope(True, depth)
                s.names |= pending_func
                stack.append(s)
                pending_func = None
            i += 1
            continue
        if t == "}":
            if len(stack) > 1 and stack[-1].start_depth == depth:
                stack.pop()
            depth -= 1
            i += 1
            continue
        if t in "([":
            depth += 1
        elif t in ")]":
            depth -= 1

        if k != "ident" or t in KEYWORDS:
            i += 1
            continue
        if prev == ".":
            i += 1
            continue
        if nxt == ":":  # struct literal key
            i += 1
            continue

        # innermost function scope (block-level `let` is attributed to the function)
        fscope = next(s for s in reversed(stack) if s.is_func)
        in_func = len(stack) > 1

        if prev == "let":
            fscope.names.add(t)
            i += 1
            continue

        if t in fscope.names:
            i += 1
            continue

        if in_func:
            if t in toplevel_lets:
                issues.append(("E001", ln, f"'{t}' is a top-level `let` (line {toplevel_lets[t]}); "
                                           f"inside a func it resolves as a global and is undefined at runtime"))
            elif t.startswith("obj_") and t not in exposed:
                issues.append(("E003", ln, f"object '{t}' is not exposed by the game"))
            elif t not in exposed and t not in toplevel_globals and nxt == "(":
                issues.append(("E002", ln, f"call to unknown function '{t}'"))
        else:
            if t.startswith("obj_") and t not in exposed:
                issues.append(("E003", ln, f"object '{t}' is not exposed by the game"))
            elif t in toplevel_globals and toplevel_globals[t] > ln and nxt != "=":
                issues.append(("W002", ln, f"'{t}' used before it is assigned (line {toplevel_globals[t]})"))
            elif (t not in exposed and t not in toplevel_globals and t not in toplevel_lets
                  and nxt == "("):
                issues.append(("E002", ln, f"call to unknown function '{t}'"))
        i += 1

    # self is a keyword so it is skipped above; scan for it separately.
    depth_func = 0
    stack2 = [False]
    for i, (k, t, ln) in enumerate(toks):
        if t == "self" and i + 1 < len(toks) and toks[i + 1][1] == "." and any(stack2[1:]):
            issues.append(("W001", ln, "`self.` inside a func is the GML instance/file globals, not the struct"))
        if t in ("func", "fun"):
            depth_func += 1
        if t == "{":
            stack2.append(depth_func > 0 and toks[i - 1][1] == ")" and _is_func_body(toks, i))
        elif t == "}" and len(stack2) > 1:
            stack2.pop()
    return issues


def _is_func_body(toks, brace_idx):
    # walk back over the parameter list to see if it is preceded by func/fun
    j = brace_idx - 1
    if toks[j][1] != ")":
        return False
    d = 0
    while j >= 0:
        if toks[j][1] == ")":
            d += 1
        elif toks[j][1] == "(":
            d -= 1
            if d == 0:
                return j > 0 and toks[j - 1][1] in ("func", "fun")
        j -= 1
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--exposed", default=str(Path(__file__).resolve().parent.parent
                                             / "docs" / "api" / "exposed_values.txt"))
    args = ap.parse_args()
    exposed = {l.strip() for l in Path(args.exposed).read_text(encoding="utf-8").splitlines() if l.strip()}
    issues = lint(args.script, exposed)
    seen = set()
    errors = 0
    for code, ln, msg in sorted(issues, key=lambda x: (x[1], x[0])):
        if (code, ln, msg) in seen:
            continue
        seen.add((code, ln, msg))
        errors += code.startswith("E")
        print(f"{args.script}:{ln}: {code} {msg}")
    warnings = len(seen) - errors
    print(f"\n{errors} error(s), {warnings} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
