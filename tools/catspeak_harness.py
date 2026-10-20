#!/usr/bin/env python3
"""
Headless playtest harness for Zero Sievert Catspeak mods.

A small Catspeak 3.1.1 interpreter (the subset DREAD uses) plus a mocked Zero
Sievert modding API. It runs the real mod script, fires game events and steps
the player frame by frame, so crashes and balance can be measured without
launching the game.

Faithful to the game where it matters for crashes:
  * Name resolution follows Catspeak 3.1.1's compiler (scr_catspeak_ir.gml
    createGet): only the *current* function's blocks are searched, then exposed
    API names, then the file's dynamic globals. No closures.
  * Runtime errors mirror GML/Catspeak: calling a non-function, indexing
    undefined, string + number, arithmetic on undefined, bad array indexes.
  * API mocks validate arguments against ZS_vanilla gamedata (NPC presets,
    factions, chest ids, armor ids, events) and the exposed values list.

Not modelled: rendering, AI, real map collision (CollisionWalkable is a
configurable random model), the real Catspeak parser's every corner case.

Usage (library): see tools/simulate_raids.py
"""
import math
import random
import re
from pathlib import Path


# -----------------------------------------------------------------------------
# Values
# -----------------------------------------------------------------------------

class _Undefined:
    _inst = None

    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self):
        return "undefined"


UNDEF = _Undefined()


class CatError(Exception):
    """A runtime error the game would report as a crash."""

    def __init__(self, msg, line=None):
        super().__init__(msg)
        self.msg = msg
        self.line = line

    def __str__(self):
        return f"line {self.line}: {self.msg}" if self.line else self.msg


class CatSyntaxError(Exception):
    pass


class Struct(dict):
    """A GML struct (also used for instances)."""
    __hash__ = object.__hash__

    def __eq__(self, other):
        return self is other


class ObjRef:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class CatFunc:
    def __init__(self, body, nlocals, nparams, name="<func>"):
        self.body = body
        self.nlocals = nlocals
        self.nparams = nparams
        self.name = name


class Native:
    def __init__(self, name, fn):
        self.name = name
        self.fn = fn


def type_name(v):
    if v is UNDEF:
        return "undefined"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, Struct):
        return "struct"
    if isinstance(v, (CatFunc, Native)):
        return "function"
    if isinstance(v, ObjRef):
        return "object"
    return type(v).__name__


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, str)


def truthy(v, line):
    if isinstance(v, bool):
        return v
    if is_num(v):
        return v > 0.5  # GML truthiness
    raise CatError(f"cannot use {type_name(v)} as a condition", line)


def gml_eq(a, b):
    if a is UNDEF or b is UNDEF:
        return a is b
    if is_num(a) and is_num(b):
        return float(a) == float(b)
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, ObjRef) and isinstance(b, ObjRef):
        return a.name == b.name
    return a is b


def to_display(v):
    if v is UNDEF:
        return "undefined"
    if isinstance(v, bool):
        return "1" if v else "0"
    if is_num(v):
        if float(v).is_integer():
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if isinstance(v, ObjRef):
        return v.name
    return str(v)


# -----------------------------------------------------------------------------
# Lexer
# -----------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r'(?P<ws>\s+)'
    r'|(?P<comment>--[^\n]*)'
    r'|(?P<str>@?"(?:\\.|[^"\\])*")'
    r'|(?P<num>\d+(?:\.\d+)?)'
    r'|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<op>==|!=|<=|>=|\+=|-=|\*=|/=|//|[{}()\[\].,:;=<>+\-*/!%])'
)

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "v": "\v", "f": "\f"}


def tokenize(src):
    toks, pos, line = [], 0, 1
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise CatSyntaxError(f"line {line}: unexpected character {src[pos]!r}")
        kind, text = m.lastgroup, m.group(m.lastgroup)
        if kind == "str":
            if text.startswith("@"):
                val = text[2:-1]
            else:
                val = re.sub(r"\\(.)", lambda mm: ESCAPES.get(mm.group(1), mm.group(1)), text[1:-1])
            toks.append(("str", val, line))
        elif kind == "num":
            toks.append(("num", float(text), line))
        elif kind not in ("ws", "comment"):
            toks.append((kind, text, line))
        line += text.count("\n")
        pos = m.end()
    toks.append(("eof", None, line))
    return toks


# -----------------------------------------------------------------------------
# Compiler: tokens -> Python closures, with Catspeak's scoping rules
# -----------------------------------------------------------------------------

class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


BINARY_PREC = {
    "or": 1, "and": 2,
    "==": 3, "!=": 3,
    "<": 4, "<=": 4, ">": 4, ">=": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "//": 6, "%": 6,
}
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/="}


class FuncScope:
    def __init__(self, params):
        self.blocks = [dict()]
        self.nlocals = 0
        for p in params:
            self.alloc(p)

    def alloc(self, name):
        idx = self.nlocals
        self.nlocals += 1
        self.blocks[-1][name] = idx
        return idx

    def lookup(self, name):
        for b in reversed(self.blocks):
            if name in b:
                return b[name]
        return None


class Compiler:
    def __init__(self, src, runtime):
        self.toks = tokenize(src)
        self.i = 0
        self.rt = runtime
        self.fscopes = []

    # token helpers
    def peek(self, k=0):
        return self.toks[self.i + k]

    def next(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def at(self, text):
        t = self.peek()
        return t[0] in ("op", "ident") and t[1] == text

    def expect(self, text):
        t = self.next()
        if t[1] != text or t[0] not in ("op", "ident"):
            raise CatSyntaxError(f"line {t[2]}: expected '{text}', got {t[1]!r}")
        return t

    # program
    def compile_program(self):
        self.fscopes.append(FuncScope([]))
        stmts = []
        while self.peek()[0] != "eof":
            s = self.statement()
            if s is not None:
                stmts.append(s)
        scope = self.fscopes.pop()
        return CatFunc(self._seq(stmts), scope.nlocals, 0, "<toplevel>")

    @staticmethod
    def _seq(stmts):
        def run(fr):
            for s in stmts:
                s(fr)
            return UNDEF
        return run

    def block(self):
        self.expect("{")
        fs = self.fscopes[-1]
        fs.blocks.append(dict())
        stmts = []
        while not self.at("}"):
            if self.peek()[0] == "eof":
                raise CatSyntaxError("unexpected end of file inside block")
            s = self.statement()
            if s is not None:
                stmts.append(s)
        self.expect("}")
        fs.blocks.pop()
        return self._seq(stmts)

    def statement(self):
        t = self.peek()
        if t[0] == "op" and t[1] == ";":
            self.next()
            return None
        if t[0] == "ident" and t[1] == "let":
            self.next()
            name_tok = self.next()
            if name_tok[0] != "ident":
                raise CatSyntaxError(f"line {name_tok[2]}: expected a name after let")
            init = None
            if self.at("="):
                self.next()
                init = self.expression()
            # allocate AFTER compiling the initialiser (not hoisted)
            idx = self.fscopes[-1].alloc(name_tok[1])
            if init is None:
                def run(fr, idx=idx):
                    fr[idx] = UNDEF
            else:
                def run(fr, idx=idx, init=init):
                    fr[idx] = init(fr)
            self._semi()
            return run
        if t[0] == "ident" and t[1] == "return":
            self.next()
            line = t[2]
            if self.at("}") or self.at(";"):
                self._semi()
                def run(fr):
                    raise _Return(UNDEF)
                return run
            e = self.expression()
            self._semi()
            def run(fr, e=e):
                raise _Return(e(fr))
            return run
        if t[0] == "ident" and t[1] == "break":
            self.next()
            self._semi()
            def run(fr):
                raise _Break()
            return run
        if t[0] == "ident" and t[1] == "continue":
            self.next()
            self._semi()
            def run(fr):
                raise _Continue()
            return run
        e = self.expression()
        self._semi()
        return e

    def _semi(self):
        if self.at(";"):
            self.next()

    # expressions
    def expression(self):
        return self.assignment()

    def assignment(self):
        start = self.i
        lhs_info = self._try_lvalue()
        if lhs_info is not None and self.peek()[0] == "op" and self.peek()[1] in ASSIGN_OPS:
            op_tok = self.next()
            rhs = self.assignment()
            return self._make_assign(lhs_info, op_tok[1], rhs, op_tok[2])
        self.i = start
        return self.binary(0)

    def _try_lvalue(self):
        """Parse a postfix expression and return a description if assignable."""
        start = self.i
        try:
            node = self.postfix(want_lvalue=True)
        except CatSyntaxError:
            self.i = start
            return None
        return node if isinstance(node, tuple) else None

    def _make_assign(self, lhs, op, rhs, line):
        kind = lhs[0]

        def combine(old, new):
            if op == "=":
                return new
            return self.rt.arith(op[0], old, new, line)

        if kind == "local":
            idx = lhs[1]

            def run(fr):
                v = combine(fr[idx], rhs(fr)) if op != "=" else rhs(fr)
                fr[idx] = v
                return UNDEF
            return run
        if kind == "global":
            name = lhs[1]
            rt = self.rt

            def run(fr):
                if op == "=":
                    rt.globals[name] = rhs(fr)
                else:
                    rt.globals[name] = combine(rt.globals.get(name, UNDEF), rhs(fr))
                return UNDEF
            return run
        if kind == "index":
            coll, key = lhs[1], lhs[2]
            rt = self.rt

            def run(fr):
                c = coll(fr)
                k = key(fr)
                if op == "=":
                    rt.index_set(c, k, rhs(fr), line)
                else:
                    rt.index_set(c, k, combine(rt.index_get(c, k, line), rhs(fr)), line)
                return UNDEF
            return run
        raise CatSyntaxError(f"line {line}: cannot assign")

    def binary(self, min_prec):
        left = self.unary()
        while True:
            t = self.peek()
            op = t[1] if t[0] in ("op", "ident") else None
            prec = BINARY_PREC.get(op)
            if prec is None or prec < min_prec:
                return left
            self.next()
            right = self.binary(prec + 1)
            left = self._make_binary(op, left, right, t[2])

    def _make_binary(self, op, a, b, line):
        rt = self.rt
        if op == "and":
            return lambda fr: truthy(a(fr), line) and truthy(b(fr), line)
        if op == "or":
            return lambda fr: truthy(a(fr), line) or truthy(b(fr), line)
        if op == "==":
            return lambda fr: gml_eq(a(fr), b(fr))
        if op == "!=":
            return lambda fr: not gml_eq(a(fr), b(fr))
        if op in ("<", "<=", ">", ">="):
            return lambda fr: rt.compare(op, a(fr), b(fr), line)
        return lambda fr: rt.arith(op, a(fr), b(fr), line)

    def unary(self):
        t = self.peek()
        if t[0] == "op" and t[1] == "!":
            self.next()
            e = self.unary()
            line = t[2]
            return lambda fr: not truthy(e(fr), line)
        if t[0] == "op" and t[1] == "-":
            self.next()
            e = self.unary()
            line = t[2]
            rt = self.rt
            return lambda fr: rt.arith("-", 0, e(fr), line)
        return self.postfix()

    def postfix(self, want_lvalue=False):
        node = self.primary()  # either closure or lvalue tuple
        while True:
            t = self.peek()
            if t[0] == "op" and t[1] == ".":
                self.next()
                name = self.next()
                if name[0] != "ident":
                    raise CatSyntaxError(f"line {name[2]}: expected field name")
                coll = self._as_expr(node)
                key = name[1]
                node = ("index", coll, (lambda fr, key=key: key), name[2], key)
            elif t[0] == "op" and t[1] == "[":
                self.next()
                k = self.expression()
                self.expect("]")
                node = ("index", self._as_expr(node), k, t[2], None)
            elif t[0] == "op" and t[1] == "(":
                self.next()
                args = []
                while not self.at(")"):
                    args.append(self.expression())
                    if self.at(","):
                        self.next()
                self.expect(")")
                node = self._make_call(node, args, t[2])
            else:
                break
        if want_lvalue:
            return node
        return self._as_expr(node)

    def _as_expr(self, node):
        if not isinstance(node, tuple):
            return node
        kind = node[0]
        rt = self.rt
        if kind == "local":
            idx = node[1]
            return lambda fr: fr[idx]
        if kind == "global":
            name = node[1]
            return lambda fr: rt.globals.get(name, UNDEF)
        if kind == "index":
            coll, key, line = node[1], node[2], node[3]
            return lambda fr: rt.index_get(coll(fr), key(fr), line)
        raise AssertionError(kind)

    def _make_call(self, node, args, line):
        rt = self.rt
        if isinstance(node, tuple) and node[0] == "index":
            coll, key = node[1], node[2]

            def run(fr):
                c = coll(fr)
                k = key(fr)
                if not (isinstance(c, (Struct, list))):
                    raise CatError(f"value is not a function, got '{type_name(c)}' (method call on {type_name(c)})", line)
                f = rt.index_get(c, k, line)
                return rt.call(f, [a(fr) for a in args], line)
            return run
        callee = self._as_expr(node)
        return lambda fr: rt.call(callee(fr), [a(fr) for a in args], line)

    def primary(self):
        t = self.next()
        kind, val, line = t
        if kind == "num":
            return lambda fr, v=val: v
        if kind == "str":
            return lambda fr, v=val: v
        if kind == "op" and val == "(":
            e = self.expression()
            self.expect(")")
            return e
        if kind == "op" and val == "[":
            items = []
            while not self.at("]"):
                items.append(self.expression())
                if self.at(","):
                    self.next()
            self.expect("]")
            return lambda fr: [it(fr) for it in items]
        if kind == "op" and val == "{":
            keys, vals = [], []
            while not self.at("}"):
                k = self.next()
                if k[0] not in ("ident", "str"):
                    raise CatSyntaxError(f"line {k[2]}: bad struct key {k[1]!r}")
                self.expect(":")
                keys.append(k[1])
                vals.append(self.expression())
                if self.at(","):
                    self.next()
            self.expect("}")

            def run(fr):
                s = Struct()
                for k, v in zip(keys, vals):
                    s[k] = v(fr)
                return s
            return run
        if kind == "ident":
            if val == "true":
                return lambda fr: True
            if val == "false":
                return lambda fr: False
            if val == "undefined":
                return lambda fr: UNDEF
            if val in ("func", "fun"):
                return self._function(line)
            if val == "if":
                return self._if(line)
            if val == "while":
                return self._while(line)
            if val == "match":
                return self._match(line)
            if val == "self":
                rt = self.rt
                return lambda fr: rt.self_value
            # identifier resolution (compile time, like Catspeak)
            idx = self.fscopes[-1].lookup(val)
            if idx is not None:
                return ("local", idx)
            if val in self.rt.api:
                v = self.rt.api[val]
                return lambda fr, v=v: v
            return ("global", val)
        raise CatSyntaxError(f"line {line}: unexpected token {val!r}")

    def _function(self, line):
        self.expect("(")
        params = []
        while not self.at(")"):
            p = self.next()
            if p[0] != "ident":
                raise CatSyntaxError(f"line {p[2]}: bad parameter")
            params.append(p[1])
            if self.at(","):
                self.next()
        self.expect(")")
        self.fscopes.append(FuncScope(params))
        body = self.block()
        scope = self.fscopes.pop()
        fn = CatFunc(body, scope.nlocals, len(params), f"func@{line}")
        return lambda fr: fn

    def _if(self, line):
        cond = self.expression()
        then = self.block()
        other = None
        if self.at("else"):
            self.next()
            if self.at("if"):
                self.next()
                other = self._if(self.peek()[2])
            else:
                other = self.block()

        def run(fr):
            if truthy(cond(fr), line):
                return then(fr)
            if other is not None:
                return other(fr)
            return UNDEF
        return run

    def _while(self, line):
        cond = self.expression()
        body = self.block()
        rt = self.rt

        def run(fr):
            n = 0
            while truthy(cond(fr), line):
                n += 1
                if n > rt.loop_limit:
                    raise CatError("infinite loop (game would hang)", line)
                try:
                    body(fr)
                except _Break:
                    break
                except _Continue:
                    continue
            return UNDEF
        return run

    def _match(self, line):
        subject = self.expression()
        self.expect("{")
        cases, default = [], None
        while not self.at("}"):
            if self.at("case"):
                self.next()
                v = self.expression()
                cases.append((v, self.block()))
            elif self.at("else"):
                self.next()
                default = self.block()
            else:
                t = self.peek()
                raise CatSyntaxError(f"line {t[2]}: expected case/else in match, got {t[1]!r}")
        self.expect("}")

        def run(fr):
            s = subject(fr)
            for v, body in cases:
                if gml_eq(s, v(fr)):
                    return body(fr)
            if default is not None:
                return default(fr)
            return UNDEF
        return run


# -----------------------------------------------------------------------------
# Runtime
# -----------------------------------------------------------------------------

class Runtime:
    def __init__(self, api=None):
        self.globals = {}
        self.api = api or {}
        self.self_value = Struct()  # the GML instance / globals; not the struct
        self.loop_limit = 100000
        self.call_depth = 0
        # lenient: swallow index errors (returns undefined) so a design can be
        # measured even when it would crash in game. Never use for crash tests.
        self.lenient = False
        self.lenient_hits = []

    def call(self, f, args, line):
        if isinstance(f, Native):
            return f.fn(*args)
        if not isinstance(f, CatFunc):
            raise CatError(f"value is not a function, got '{type_name(f)}'", line)
        self.call_depth += 1
        if self.call_depth > 500:
            raise CatError("stack overflow", line)
        fr = [UNDEF] * max(f.nlocals, 1)
        for i in range(min(len(args), f.nparams)):
            fr[i] = args[i]
        try:
            f.body(fr)
            return UNDEF
        except _Return as r:
            return r.value
        finally:
            self.call_depth -= 1

    def index_get(self, c, k, line):
        if self.lenient:
            try:
                return self._index_get(c, k, line)
            except CatError as e:
                self.lenient_hits.append(str(e))
                return UNDEF
        return self._index_get(c, k, line)

    def _index_get(self, c, k, line):
        if isinstance(c, list):
            if not is_num(k):
                raise CatError(f"array index must be a number, got {type_name(k)} '{to_display(k)}'", line)
            ki = int(k)
            if ki < 0 or ki >= len(c):
                raise CatError(f"array index {ki} out of range (length {len(c)})", line)
            return c[ki]
        if isinstance(c, Struct):
            return c.get(k, UNDEF)
        raise CatError(f"cannot index {type_name(c)} with '{to_display(k)}'", line)

    def index_set(self, c, k, v, line):
        if isinstance(c, list):
            if not is_num(k):
                raise CatError(f"array index must be a number, got {type_name(k)}", line)
            ki = int(k)
            if ki < 0:
                raise CatError("negative array index", line)
            while len(c) <= ki:
                c.append(0)
            c[ki] = v
            return
        if isinstance(c, Struct):
            c[k] = v
            return
        raise CatError(f"cannot set field '{to_display(k)}' on {type_name(c)}", line)

    def arith(self, op, a, b, line):
        if op == "+" and isinstance(a, str) and isinstance(b, str):
            return a + b
        if not (is_num(a) and is_num(b)):
            raise CatError(f"invalid operands for '{op}': {type_name(a)} and {type_name(b)}", line)
        a, b = float(a), float(b)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise CatError("division by zero", line)
            return a / b
        if op == "//":
            if b == 0:
                raise CatError("division by zero", line)
            return float(math.trunc(a / b))
        if op == "%":
            if b == 0:
                raise CatError("division by zero", line)
            return math.fmod(a, b)
        raise CatError(f"unknown operator {op}", line)

    def compare(self, op, a, b, line):
        if not ((is_num(a) and is_num(b)) or (isinstance(a, str) and isinstance(b, str))):
            raise CatError(f"cannot compare {type_name(a)} {op} {type_name(b)}", line)
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        return a >= b


# -----------------------------------------------------------------------------
# Zero Sievert API mock
# -----------------------------------------------------------------------------

GAME_EVENTS = {"enter_hub", "enter_raid", "exit_train", "player_spawn", "player_death", "trade_completed"}
OBJECT_EVENTS = {"create_event", "step_begin_event", "step_normal_event", "step_end_event",
                 "draw_normal_event", "draw_end_event", "destroy_event", "cleanup_event"}
# Faction names from the API docs. The real game rejected "Bandits" at load in
# 0.3.0, so this is NOT the game's faction table; World(factions=...) lets
# scenarios model other tables (e.g. FACTIONS_UNKNOWN_IDS).
FACTIONS = {"Player", "Loners", "Green Army", "Crimson Corporation", "Scientists", "Bandits",
            "Mutants", "Watcher", "All Enemy", "All Friend", "Horizon"}
FACTIONS_UNKNOWN_IDS = {"player"}


def _load_lenient_json(path):
    import json
    s = Path(path).read_text(encoding="utf-8")
    return json.loads(re.sub(r",(\s*[\]}])", r"\1", s))


class World:
    """Mutable game state the mocks read and write."""

    def __init__(self, seed=0, map_w=3000, map_h=3000, walkable_ratio=0.85, factions=FACTIONS,
                 faction_create_works=True):
        self.rng = random.Random(seed)
        self.room = "r_menu"
        self.map_w, self.map_h = map_w, map_h
        self.walkable_ratio = walkable_ratio
        self.player = Struct(x=0.0, y=0.0)
        self.player_present = False
        self.events = {}
        self.object_scripts = {}
        self.npc_defs = {}
        self.spawns = []        # dicts describing every enemy that appeared
        self.popups = []
        self.filedata = {}
        self.frame = 0
        self.warnings = []
        self.factions = set(factions)
        self.faction_relations = {}
        self.faction_create_works = faction_create_works
        self.debug_log = []


def build_api(world, exposed, gamedata_dir=None, filedata_missing="empty", lenient=False):
    """Returns {name: value} for every exposed name (unmocked functions raise)."""
    presets, chests, armors = set(), set(), set()
    if gamedata_dir:
        g = Path(gamedata_dir)
        presets = set(_load_lenient_json(g / "npc_preset.json")["data"].keys()) - {"general"}
        chests = set(re.findall(r'^\t\t"([a-z0-9_]+)"\s*:', (g / "chest.json").read_text(encoding="utf-8"), re.M))
        armors = set(re.findall(r'^\t\t"([a-z0-9_]+)"\s*:', (g / "armor.json").read_text(encoding="utf-8"), re.M))
    rng = world.rng

    def need(cond, msg):
        if not cond:
            if lenient:
                world.warnings.append(msg)
                return
            raise CatError(msg)

    def npc_def(npc_id):
        need(npc_id in world.npc_defs, f"NPC '{npc_id}' used before NpcCreate")
        return world.npc_defs[npc_id]

    def NpcCreate(npc_id):
        need(isinstance(npc_id, str), "NpcCreate: id must be a string")
        world.npc_defs[npc_id] = {"preset": "hunter_intermediate", "faction": "Loners", "hp": 60,
                                  "chest": "loner_armor_2", "armor": "no_item", "xp": 22,
                                  "recoil": None}

    def NpcSetPreset(npc_id, preset):
        if presets:
            need(preset in presets, f"NpcSetPreset: unknown preset '{to_display(preset)}'")
        npc_def(npc_id)["preset"] = preset

    def NpcSetFaction(npc_id, faction):
        need(faction in world.factions, f"NpcSetFaction: unknown faction '{to_display(faction)}'")
        npc_def(npc_id)["faction"] = faction

    def FactionExists(faction):
        return faction in world.factions

    def FactionCreate(faction):
        need(isinstance(faction, str), "FactionCreate: id must be a string")
        if world.faction_create_works:
            world.factions.add(faction)

    def FactionSetRelationship(a, b, value):
        need(a in world.factions and b in world.factions,
             f"FactionSetRelationship: unknown faction '{to_display(a)}' or '{to_display(b)}'")
        need(is_num(value), "FactionSetRelationship: value must be a number")
        world.faction_relations[(a, b)] = float(value)

    def NpcSetHp(npc_id, hp):
        need(is_num(hp) and hp > 0, f"NpcSetHp: bad hp {to_display(hp)}")
        npc_def(npc_id)["hp"] = float(hp)

    def NpcSetRecoilAimRadius(npc_id, rmin=UNDEF, rmax=UNDEF):
        need(is_num(rmin) and is_num(rmax),
             f"NpcSetRecoilAimRadius: needs (id, min, max), got min={to_display(rmin)} max={to_display(rmax)}")
        if is_num(rmin) and is_num(rmax):
            need(rmin <= rmax, "NpcSetRecoilAimRadius: min > max")
            npc_def(npc_id)["recoil"] = (float(rmin), float(rmax))
        elif is_num(rmin):
            npc_def(npc_id)["recoil"] = (float(rmin), None)

    def NpcSetArmor(npc_id, armor):
        if armors:
            need(armor == "no_item" or armor in armors, f"NpcSetArmor: unknown armor '{to_display(armor)}'")
        npc_def(npc_id)["armor"] = armor

    def NpcSetChestDropped(npc_id, chest):
        if chests:
            need(chest in chests, f"NpcSetChestDropped: unknown chest '{to_display(chest)}'")
        npc_def(npc_id)["chest"] = chest

    def NpcSetExperience(npc_id, xp):
        need(is_num(xp), f"NpcSetExperience: xp must be a number, got {type_name(xp)}")
        npc_def(npc_id)["xp"] = float(xp)

    def NpcSpawn(npc_id, x, y):
        d = dict(npc_def(npc_id))
        need(is_num(x) and is_num(y), "NpcSpawn: bad position")
        world.spawns.append({"kind": "npc", "id": npc_id, "x": x, "y": y, "def": d,
                             "frame": world.frame, "chase": False})

    def InstanceCreate(x, y, obj):
        need(isinstance(obj, ObjRef), f"InstanceCreate: object index is {type_name(obj)}")
        need(is_num(x) and is_num(y), "InstanceCreate: bad position")
        world.spawns.append({"kind": "obj", "obj": obj.name, "x": x, "y": y,
                             "frame": world.frame, "chase": False})

    def NpcObjectSpawnNearPlayer(obj, amount=1, chase=False):
        need(isinstance(obj, ObjRef), f"NpcObjectSpawnNearPlayer: object is {type_name(obj)}")
        need(world.player_present, "NpcObjectSpawnNearPlayer: no player")
        for _ in range(int(amount)):
            world.spawns.append({"kind": "obj", "obj": obj.name, "x": world.player["x"],
                                 "y": world.player["y"], "frame": world.frame,
                                 "chase": bool(chase), "near_player": True})

    def CollisionWalkable(x, y):
        need(is_num(x) and is_num(y), "CollisionWalkable: bad position")
        if x < 0 or y < 0 or x > world.map_w or y > world.map_h:
            return False
        return rng.random() < world.walkable_ratio

    def EventAssignFunction(name, fn):
        need(name in GAME_EVENTS, f"EventAssignFunction: unknown event '{to_display(name)}'")
        need(isinstance(fn, CatFunc), "EventAssignFunction: not a function")
        world.events.setdefault(name, []).append(fn)

    def ObjectSetScript(obj_id, event, fn):
        need(event in OBJECT_EVENTS, f"ObjectSetScript: unknown event '{to_display(event)}'")
        need(isinstance(fn, CatFunc), "ObjectSetScript: not a function")
        key = (obj_id, event)
        if key in world.object_scripts:
            world.warnings.append(f"ObjectSetScript replaced existing {key}")
        world.object_scripts[key] = fn

    def ObjectGetAllInstances(obj):
        need(isinstance(obj, ObjRef), "ObjectGetAllInstances: needs an object index")
        if obj.name == "obj_player" and world.player_present:
            return [world.player]
        return []

    def ShowMessage(msg=UNDEF):
        world.popups.append(to_display(msg))

    def FileDataRead(key):
        if key in world.filedata:
            return world.filedata[key]
        return Struct() if filedata_missing == "empty" else UNDEF

    def FileDataWrite(key, value):
        world.filedata[key] = value

    def Irandom(n):
        need(is_num(n), f"Irandom: needs a number, got {type_name(n)}")
        n = int(math.floor(n))
        return float(rng.randint(0, n)) if n >= 0 else float(-rng.randint(0, -n))

    def String(v=UNDEF):
        return to_display(v)

    def Round(v):
        need(is_num(v), f"Round: needs a number, got {type_name(v)}")
        return float(math.floor(v + 0.5)) if v >= 0 else float(-math.floor(-v + 0.5))  # GML rounds half away? close enough

    def Clamp(v, lo, hi):
        need(is_num(v) and is_num(lo) and is_num(hi), "Clamp: needs numbers")
        return float(min(max(v, lo), hi))

    def ArrayLength(a):
        need(isinstance(a, list), f"ArrayLength: expected array, got {type_name(a)}")
        return float(len(a)) if isinstance(a, list) else 0.0

    def ArrayPush(a, *vals):
        need(isinstance(a, list), f"ArrayPush: expected array, got {type_name(a)}")
        a.extend(vals)

    num = lambda name, f: Native(name, lambda *a: (need(all(is_num(x) for x in a), f"{name}: needs numbers") or f(*a)))
    natives = {
        "NpcCreate": NpcCreate, "NpcSetPreset": NpcSetPreset, "NpcSetFaction": NpcSetFaction,
        "FactionExists": FactionExists, "FactionCreate": FactionCreate,
        "FactionSetRelationship": FactionSetRelationship,
        "NpcSetHp": NpcSetHp, "NpcSetRecoilAimRadius": NpcSetRecoilAimRadius,
        "NpcSetArmor": NpcSetArmor, "NpcSetChestDropped": NpcSetChestDropped,
        "NpcSetExperience": NpcSetExperience, "NpcSpawn": NpcSpawn,
        "InstanceCreate": InstanceCreate, "NpcObjectSpawnNearPlayer": NpcObjectSpawnNearPlayer,
        "CollisionWalkable": CollisionWalkable, "EventAssignFunction": EventAssignFunction,
        "ObjectSetScript": ObjectSetScript, "ObjectGetAllInstances": ObjectGetAllInstances,
        "ShowMessage": ShowMessage,
        "ShowDebugMessage": lambda msg=UNDEF: world.debug_log.append(to_display(msg)), "FileDataRead": FileDataRead, "FileDataWrite": FileDataWrite,
        "Irandom": Irandom, "String": String, "Round": Round, "Clamp": Clamp,
        "ArrayLength": ArrayLength, "ArrayPush": ArrayPush,
        "RoomGetCurrent": lambda: world.room,
        "KeyboardCheckPressed": lambda key: False,
        "KeyboardCheck": lambda key: False,
        "Ord": lambda s: float(ord(s[0])),
        "TimeGetHour": lambda: 12.0, "TimeGetMinute": lambda: 0.0, "TimeGetSecond": lambda: 0.0,
        "TimeGetDay": lambda: 1.0, "TimeGetMonth": lambda: 1.0, "TimeGetYear": lambda: 2020.0,
    }
    api = {}
    for name in exposed:
        if name in natives:
            api[name] = Native(name, natives[name])
        elif name.startswith(("obj_", "vk_", "mb_")):
            api[name] = ObjRef(name) if name.startswith("obj_") else float(abs(hash(name)) % 1000)
        else:
            def unmocked(*a, _n=name):
                raise CatError(f"harness: API function '{_n}' is not mocked")
            api[name] = Native(name, unmocked)
    for name, value in (("FACTION_REP_min", 0.0), ("FACTION_REP_enemy", 250.0), ("FACTION_REP_ally", 450.0),
                        ("FACTION_REP_join", 600.0), ("FACTION_REP_max", 1000.0)):
        api[name] = value
    api["Sqrt"] = num("Sqrt", lambda v: math.sqrt(v))
    api["Min"] = num("Min", lambda *v: float(min(v)))
    api["Max"] = num("Max", lambda *v: float(max(v)))
    api["Abs"] = num("Abs", lambda v: float(abs(v)))
    api["LengthDirX"] = num("LengthDirX", lambda d, a: d * math.cos(math.radians(a)))
    api["LengthDirY"] = num("LengthDirY", lambda d, a: -d * math.sin(math.radians(a)))
    api["PointDistance"] = num("PointDistance", lambda x1, y1, x2, y2: math.hypot(x2 - x1, y2 - y1))
    return api


# -----------------------------------------------------------------------------
# Session: load a mod and drive it like the game does
# -----------------------------------------------------------------------------

class ModSession:
    def __init__(self, script_path, exposed_path, gamedata_dir=None, seed=0, filedata_missing="empty",
                 lenient=False, src_transform=None, **world_kw):
        self.world = World(seed=seed, **world_kw)
        exposed = [l.strip() for l in Path(exposed_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        self.rt = Runtime(build_api(self.world, exposed, gamedata_dir, filedata_missing, lenient))
        self.rt.lenient = lenient
        self.src = Path(script_path).read_text(encoding="utf-8")
        if src_transform:
            self.src = src_transform(self.src)
        self.program = Compiler(self.src, self.rt).compile_program()

    def load(self):
        """Runs the script's top level (what the game does when mods are rebuilt)."""
        self.rt.call(self.program, [], None)

    def fire(self, event):
        for fn in self.world.events.get(event, []):
            self.rt.call(fn, [], None)

    def step(self, frames=1, event="step_end_event"):
        scripts = [fn for (obj, ev), fn in self.world.object_scripts.items()
                   if obj == "obj_player" and ev in ("step_begin_event", "step_normal_event", "step_end_event")]
        for _ in range(frames):
            self.world.frame += 1
            for fn in scripts:
                self.rt.call(fn, [self.world.player], None)

    def enter_room(self, room, player_xy=None):
        self.world.room = room
        if player_xy is not None:
            self.world.player["x"], self.world.player["y"] = float(player_xy[0]), float(player_xy[1])
            self.world.player_present = True
