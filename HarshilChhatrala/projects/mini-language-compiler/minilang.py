#!/usr/bin/env python3
"""
MiniLang - a tiny programming language and its complete compiler pipeline.

    Source -> [1 Lexer] -> tokens -> [2 Parser] -> AST -> [3 Semantic Analysis]
           -> [4 TAC generation] -> [5 Optimizer] -> [6 Code generator]
           -> stack-machine bytecode -> [7 Virtual Machine] -> output

Usage:
    python minilang.py                 # compile + run the built-in example
    python minilang.py prog.ml         # compile + run a file
    python minilang.py prog.ml --no-opt --trace
    python minilang.py --demo          # run all built-in sample programs

----------------------------------------------------------------------------
MINILANG GRAMMAR (EBNF)
----------------------------------------------------------------------------
program     -> statement* EOF
statement   -> letStmt | assignStmt | printStmt | ifStmt | whileStmt | block
letStmt     -> "let" IDENT "=" expr ";"
assignStmt  -> IDENT "=" expr ";"
printStmt   -> "print" expr ";"
ifStmt      -> "if" "(" expr ")" block [ "else" block ]
whileStmt   -> "while" "(" expr ")" block
block       -> "{" statement* "}"
expr        -> additive [ ( ">" | "<" | "==" | "!=" ) additive ]
additive    -> term ( ( "+" | "-" ) term )*
term        -> unary ( ( "*" | "/" ) unary )*
unary       -> "-" unary | primary
primary     -> NUMBER | IDENT | "(" expr ")"

Comments start with // and run to the end of the line.
Types: variables are integers; comparisons produce a boolean that may only be
used as an if/while condition.  Division truncates toward zero.
"""

import re
import sys
import argparse
from collections import namedtuple
from dataclasses import dataclass, fields, is_dataclass, field
from typing import List, Optional, Any


# ============================================================================
# Errors
# ============================================================================
class MiniLangError(Exception):
    phase = "Error"


class LexError(MiniLangError):
    phase = "Lexical error"


class ParseError(MiniLangError):
    phase = "Syntax error"


class SemanticError(MiniLangError):
    phase = "Semantic error"


class MiniLangRuntimeError(MiniLangError):
    phase = "Runtime error"


# ============================================================================
# PHASE 1: LEXICAL ANALYSIS
# ============================================================================
Token = namedtuple("Token", "type value line col")

KEYWORDS = {"let", "print", "if", "else", "while"}

TOKEN_SPEC = [
    ("COMMENT", r"//[^\n]*"),
    ("NEWLINE", r"\n"),
    ("SPACE", r"[ \t\r]+"),
    ("NUMBER", r"\d+"),
    ("IDENT", r"[A-Za-z_]\w*"),
    ("OP", r"==|!=|[+\-*/<>=]"),
    ("PUNCT", r"[(){};]"),
    ("BAD", r"."),
]
TOKEN_RE = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC))


class Lexer:
    def __init__(self, source: str):
        self.source = source

    def tokenize(self) -> List[Token]:
        tokens, line, line_start = [], 1, 0
        for m in TOKEN_RE.finditer(self.source):
            kind, text = m.lastgroup, m.group()
            col = m.start() - line_start + 1
            if kind == "NEWLINE":
                line += 1
                line_start = m.end()
            elif kind in ("SPACE", "COMMENT"):
                continue
            elif kind == "BAD":
                raise LexError(f"line {line}, col {col}: unexpected character {text!r}")
            elif kind == "IDENT":
                ttype = text.upper() if text in KEYWORDS else "IDENT"
                tokens.append(Token(ttype, text, line, col))
            elif kind == "NUMBER":
                tokens.append(Token("NUMBER", text, line, col))
            else:  # OP / PUNCT: the token type is the symbol itself
                tokens.append(Token(text, text, line, col))
        tokens.append(Token("EOF", "", line, 1))
        return tokens


# ============================================================================
# PHASE 2: PARSER (recursive descent) + AST
# ============================================================================
class Node:
    pass


@dataclass
class Num(Node):
    value: int
    line: int = 0


@dataclass
class Var(Node):
    name: str
    line: int = 0
    uid: Optional[str] = None  # unique name, filled in by semantic analysis


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node
    line: int = 0


@dataclass
class Let(Node):
    name: str
    expr: Node
    line: int = 0
    uid: Optional[str] = None


@dataclass
class Assign(Node):
    name: str
    expr: Node
    line: int = 0
    uid: Optional[str] = None


@dataclass
class Print(Node):
    expr: Node
    line: int = 0


@dataclass
class Block(Node):
    stmts: List[Node] = field(default_factory=list)


@dataclass
class If(Node):
    cond: Node
    then: Block
    orelse: Optional[Block] = None
    line: int = 0


@dataclass
class While(Node):
    cond: Node
    body: Block
    line: int = 0


@dataclass
class Program(Node):
    stmts: List[Node] = field(default_factory=list)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.toks, self.pos = tokens, 0

    # -- helpers --
    @property
    def cur(self) -> Token:
        return self.toks[self.pos]

    def advance(self) -> Token:
        t = self.cur
        self.pos += 1
        return t

    def check(self, *types) -> bool:
        return self.cur.type in types

    def expect(self, ttype: str) -> Token:
        if not self.check(ttype):
            t = self.cur
            found = "end of input" if t.type == "EOF" else repr(t.value)
            raise ParseError(f"line {t.line}, col {t.col}: expected {ttype!r} but found {found}")
        return self.advance()

    # -- grammar rules --
    def parse(self) -> Program:
        stmts = []
        while not self.check("EOF"):
            stmts.append(self.statement())
        return Program(stmts)

    def statement(self) -> Node:
        t = self.cur
        if t.type == "LET":
            self.advance()
            name = self.expect("IDENT").value
            self.expect("=")
            e = self.expr()
            self.expect(";")
            return Let(name, e, t.line)
        if t.type == "PRINT":
            self.advance()
            e = self.expr()
            self.expect(";")
            return Print(e, t.line)
        if t.type == "IF":
            self.advance()
            self.expect("(")
            cond = self.expr()
            self.expect(")")
            then = self.block()
            orelse = None
            if self.check("ELSE"):
                self.advance()
                orelse = self.block()
            return If(cond, then, orelse, t.line)
        if t.type == "WHILE":
            self.advance()
            self.expect("(")
            cond = self.expr()
            self.expect(")")
            return While(cond, self.block(), t.line)
        if t.type == "{":
            return self.block()
        if t.type == "IDENT":
            self.advance()
            self.expect("=")
            e = self.expr()
            self.expect(";")
            return Assign(t.value, e, t.line)
        found = "end of input" if t.type == "EOF" else repr(t.value)
        raise ParseError(f"line {t.line}, col {t.col}: unexpected {found}, expected a statement")

    def block(self) -> Block:
        self.expect("{")
        stmts = []
        while not self.check("}", "EOF"):
            stmts.append(self.statement())
        self.expect("}")
        return Block(stmts)

    def expr(self) -> Node:
        left = self.additive()
        if self.check(">", "<", "==", "!="):
            op = self.advance()
            left = Binary(op.value, left, self.additive(), op.line)
        return left

    def additive(self) -> Node:
        left = self.term()
        while self.check("+", "-"):
            op = self.advance()
            left = Binary(op.value, left, self.term(), op.line)
        return left

    def term(self) -> Node:
        left = self.unary()
        while self.check("*", "/"):
            op = self.advance()
            left = Binary(op.value, left, self.unary(), op.line)
        return left

    def unary(self) -> Node:
        if self.check("-"):
            op = self.advance()
            return Binary("-", Num(0, op.line), self.unary(), op.line)  # -x  ==>  0 - x
        return self.primary()

    def primary(self) -> Node:
        t = self.cur
        if t.type == "NUMBER":
            self.advance()
            return Num(int(t.value), t.line)
        if t.type == "IDENT":
            self.advance()
            return Var(t.value, t.line)
        if t.type == "(":
            self.advance()
            e = self.expr()
            self.expect(")")
            return e
        found = "end of input" if t.type == "EOF" else repr(t.value)
        raise ParseError(f"line {t.line}, col {t.col}: unexpected {found}, expected an expression")


def dump_ast(node: Any, indent: int = 0) -> str:
    """Pretty-print an AST as an indented tree."""
    pad = "  " * indent
    if isinstance(node, list):
        return "".join(dump_ast(n, indent) for n in node)
    scalars, children = [], []
    for f in fields(node):
        v = getattr(node, f.name)
        if f.name in ("line", "uid"):
            continue
        if isinstance(v, (Node, list)) and v != []:
            children.append((f.name, v))
        elif v is not None and v != []:
            scalars.append(f"{f.name}={v!r}")
    out = f"{pad}{type(node).__name__}({', '.join(scalars)})\n"
    for name, child in children:
        if isinstance(child, list):
            out += dump_ast(child, indent + 1)
        else:
            out += f"{pad}  {name}:\n" + dump_ast(child, indent + 2)
    return out


# ============================================================================
# PHASE 3: SEMANTIC ANALYSIS
# ============================================================================
class SemanticAnalyzer:
    """
    Checks:  declared before use | no redeclaration in the same scope |
             arithmetic on ints only | print/let/assign need an int |
             if/while conditions must be boolean | constant division by zero.
    Also gives every variable a unique name (handles shadowing in blocks).
    """

    def __init__(self):
        self.scopes: List[dict] = [{}]
        self.counts: dict = {}
        self.errors: List[str] = []
        self.symbols: List[tuple] = []  # (name, unique name, type, scope depth, line)

    def err(self, line, msg):
        self.errors.append(f"line {line}: {msg}")

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def declare(self, name, line):
        if name in self.scopes[-1]:
            self.err(line, f"variable '{name}' is already declared in this scope")
        n = self.counts.get(name, 0)
        uid = name if n == 0 else f"{name}_{n}"
        self.counts[name] = n + 1
        self.scopes[-1][name] = uid
        self.symbols.append((name, uid, "int", len(self.scopes) - 1, line))
        return uid

    def analyze(self, prog: Program):
        for s in prog.stmts:
            self.stmt(s)
        if self.errors:
            raise SemanticError("\n".join(self.errors))
        return self.symbols

    def stmt(self, s):
        if isinstance(s, Let):
            t = self.expr(s.expr)  # analysed first: `let x = x + 1` sees the OUTER x
            if t == "bool":
                self.err(s.line, "cannot store a boolean in variable (variables are int)")
            s.uid = self.declare(s.name, s.line)
        elif isinstance(s, Assign):
            t = self.expr(s.expr)
            s.uid = self.lookup(s.name)
            if s.uid is None:
                self.err(s.line, f"assignment to undeclared variable '{s.name}'")
            if t == "bool":
                self.err(s.line, "cannot assign a boolean to an int variable")
        elif isinstance(s, Print):
            if self.expr(s.expr) == "bool":
                self.err(s.line, "cannot print a boolean value (print takes an int)")
        elif isinstance(s, If):
            if self.expr(s.cond) != "bool":
                self.err(s.line, "if-condition must be a comparison (e.g. x > 0)")
            self.block(s.then)
            if s.orelse:
                self.block(s.orelse)
        elif isinstance(s, While):
            if self.expr(s.cond) != "bool":
                self.err(s.line, "while-condition must be a comparison (e.g. i < 10)")
            self.block(s.body)
        elif isinstance(s, Block):
            self.block(s)

    def block(self, b: Block):
        self.scopes.append({})
        for s in b.stmts:
            self.stmt(s)
        self.scopes.pop()

    def expr(self, e) -> str:
        if isinstance(e, Num):
            return "int"
        if isinstance(e, Var):
            e.uid = self.lookup(e.name)
            if e.uid is None:
                self.err(e.line, f"use of undeclared variable '{e.name}'")
            return "int"
        lt, rt = self.expr(e.left), self.expr(e.right)
        if lt != "int" or rt != "int":
            self.err(e.line, f"operator '{e.op}' needs int operands, got {lt} and {rt}")
        if e.op == "/" and isinstance(e.right, Num) and e.right.value == 0:
            self.err(e.line, "division by constant zero")
        return "bool" if e.op in (">", "<", "==", "!=") else "int"


# ============================================================================
# PHASE 4: INTERMEDIATE CODE - THREE-ADDRESS CODE
# ============================================================================
# TAC(op, a, b, r):
#   copy  : r = a              binary ops: r = a <op> b
#   label : r:                 goto : goto r
#   ifFalse: ifFalse a goto r  print : print a
TAC = namedtuple("TAC", "op a b r")
BINOPS = {"+", "-", "*", "/", ">", "<", "==", "!="}


def format_tac(i: TAC) -> str:
    if i.op == "copy":
        return f"{i.r} = {i.a}"
    if i.op in BINOPS:
        return f"{i.r} = {i.a} {i.op} {i.b}"
    if i.op == "label":
        return f"{i.r}:"
    if i.op == "goto":
        return f"    goto {i.r}"
    if i.op == "ifFalse":
        return f"    ifFalse {i.a} goto {i.r}"
    if i.op == "print":
        return f"    print {i.a}"
    return str(i)


def show_tac(code: List[TAC]) -> str:
    out = []
    for n, i in enumerate(code):
        text = format_tac(i)
        text = text if i.op == "label" else "    " + text.strip()
        out.append(f"{n:3}  {text}")
    return "\n".join(out)


class TACGenerator:
    def __init__(self):
        self.code: List[TAC] = []
        self.ntemp = 0
        self.nlabel = 0

    def temp(self):
        self.ntemp += 1
        return f"t{self.ntemp}"

    def label(self):
        self.nlabel += 1
        return f"L{self.nlabel}"

    def emit(self, op, a=None, b=None, r=None):
        self.code.append(TAC(op, a, b, r))

    def generate(self, prog: Program) -> List[TAC]:
        for s in prog.stmts:
            self.stmt(s)
        return self.code

    def stmt(self, s):
        if isinstance(s, (Let, Assign)):
            self.expr(s.expr, dest=s.uid)
        elif isinstance(s, Print):
            self.emit("print", self.expr(s.expr))
        elif isinstance(s, Block):
            for x in s.stmts:
                self.stmt(x)
        elif isinstance(s, If):
            c = self.expr(s.cond)
            l_else, l_end = self.label(), self.label()
            self.emit("ifFalse", c, None, l_else)
            self.stmt(s.then)
            if s.orelse:
                self.emit("goto", r=l_end)
                self.emit("label", r=l_else)
                self.stmt(s.orelse)
                self.emit("label", r=l_end)
            else:
                self.emit("label", r=l_else)
        elif isinstance(s, While):
            l_start, l_end = self.label(), self.label()
            self.emit("label", r=l_start)
            c = self.expr(s.cond)
            self.emit("ifFalse", c, None, l_end)
            self.stmt(s.body)
            self.emit("goto", r=l_start)
            self.emit("label", r=l_end)

    def expr(self, e, dest=None) -> str:
        """Returns the operand (constant, variable or temp) holding the value.
        If `dest` is given, the value is stored there."""
        if isinstance(e, Num):
            res = str(e.value)
        elif isinstance(e, Var):
            res = e.uid
        else:
            a = self.expr(e.left)
            b = self.expr(e.right)
            r = dest or self.temp()
            self.emit(e.op, a, b, r)
            return r
        if dest:
            self.emit("copy", res, None, dest)
            return dest
        return res


# ============================================================================
# PHASE 5: OPTIMIZATION
# ============================================================================
def is_const(x) -> bool:
    return x is not None and re.fullmatch(r"-?\d+", x) is not None


def eval_op(op, a: int, b: int) -> int:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":  # truncate toward zero
        q = abs(a) // abs(b)
        return q if (a < 0) == (b < 0) else -q
    return int({">": a > b, "<": a < b, "==": a == b, "!=": a != b}[op])


class Optimizer:
    """
    Passes (repeated until nothing changes):
      1. Constant folding            t = 2 * 3          ->  t = 6
      2. Constant propagation        x = 5; y = x + 1   ->  y = 6   (within a basic block)
      3. Algebraic simplification    x + 0, x * 1, x * 0 ...
      4. Branch folding              ifFalse 1 goto L   ->  (removed)
      5. Dead code elimination       unused temps / variables, unreachable code,
                                     jumps to the next instruction, unused labels
    """

    def __init__(self):
        self.log: List[str] = []

    def optimize(self, code: List[TAC]) -> List[TAC]:
        while True:
            before = list(code)
            code = self.fold(code)
            code = self.dead_stores(code)
            code = self.cleanup_flow(code)
            if code == before:
                return code

    def fold(self, code):
        env, out = {}, []

        def sub(x):
            return str(env[x]) if x in env else x

        for i in code:
            if i.op == "label":
                env.clear()  # another path may reach here: forget known values
                out.append(i)
            elif i.op == "goto":
                env.clear()
                out.append(i)
            elif i.op == "print":
                out.append(TAC("print", sub(i.a), None, None))
            elif i.op == "ifFalse":
                c = sub(i.a)
                if is_const(c):
                    if int(c) != 0:
                        self.log.append(f"branch folding: '{format_tac(i).strip()}' never jumps -> removed")
                    else:
                        self.log.append(f"branch folding: '{format_tac(i).strip()}' always jumps -> goto {i.r}")
                        out.append(TAC("goto", None, None, i.r))
                else:
                    out.append(TAC("ifFalse", c, None, i.r))
            elif i.op == "copy":
                a = sub(i.a)
                if is_const(a):
                    env[i.r] = int(a)
                else:
                    env.pop(i.r, None)
                out.append(TAC("copy", a, None, i.r))
            else:  # binary operation
                a, b = sub(i.a), sub(i.b)
                new = TAC(i.op, a, b, i.r)
                if is_const(a) and is_const(b) and not (i.op == "/" and int(b) == 0):
                    v = eval_op(i.op, int(a), int(b))
                    new = TAC("copy", str(v), None, i.r)
                    self.log.append(f"constant folding: {i.r} = {a} {i.op} {b}  ->  {i.r} = {v}")
                else:
                    simp = self.simplify(i.op, a, b)
                    if simp is not None:
                        new = TAC("copy", simp, None, i.r)
                        self.log.append(f"algebraic simplification: {i.r} = {a} {i.op} {b}  ->  {i.r} = {simp}")
                if new.op == "copy" and is_const(new.a):
                    env[i.r] = int(new.a)
                else:
                    env.pop(i.r, None)
                out.append(new)
        return out

    @staticmethod
    def simplify(op, a, b) -> Optional[str]:
        if op == "+" and b == "0":
            return a
        if op == "+" and a == "0":
            return b
        if op == "-" and b == "0":
            return a
        if op == "*" and b == "1":
            return a
        if op == "*" and a == "1":
            return b
        if op == "*" and "0" in (a, b):
            return "0"
        if op == "/" and b == "1":
            return a
        return None

    def dead_stores(self, code):
        used = set()
        for i in code:
            for x in (i.a, i.b):
                if x is not None and not is_const(x):
                    used.add(x)
        out = []
        for i in code:
            pure = i.op == "copy" or (i.op in BINOPS and i.op != "/")  # keep '/': may trap
            if pure and i.r not in used:
                self.log.append(f"dead code elimination: removed '{format_tac(i).strip()}'")
                continue
            out.append(i)
        return out

    def cleanup_flow(self, code):
        # unreachable code: everything after a goto up to the next label
        out, dead = [], False
        for i in code:
            if i.op == "label":
                dead = False
            if dead:
                self.log.append(f"unreachable code removed: '{format_tac(i).strip()}'")
                continue
            out.append(i)
            if i.op == "goto":
                dead = True
        # 'goto L' directly followed by 'L:'
        code, out = out, []
        for n, i in enumerate(code):
            if i.op == "goto" and n + 1 < len(code) and code[n + 1].op == "label" and code[n + 1].r == i.r:
                self.log.append(f"removed redundant jump to {i.r}")
                continue
            out.append(i)
        # labels nobody jumps to
        targets = {i.r for i in out if i.op in ("goto", "ifFalse")}
        return [i for i in out if not (i.op == "label" and i.r not in targets)]


# ============================================================================
# PHASE 6: TARGET CODE - stack-machine bytecode
# ============================================================================
Instr = namedtuple("Instr", "op arg")
ARITH = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", ">": "GT", "<": "LT", "==": "EQ", "!=": "NE"}


class CodeGenerator:
    """TAC -> stack machine.  Every variable/temp lives in a named memory cell."""

    def generate(self, tac: List[TAC]):
        raw = []  # contains ('LABEL', name) pseudo-instructions

        def push(x):
            raw.append(Instr("PUSH", int(x)) if is_const(x) else Instr("LOAD", x))

        for i in tac:
            if i.op == "copy":
                push(i.a)
                raw.append(Instr("STORE", i.r))
            elif i.op in ARITH:
                push(i.a)
                push(i.b)
                raw.append(Instr(ARITH[i.op], None))
                raw.append(Instr("STORE", i.r))
            elif i.op == "print":
                push(i.a)
                raw.append(Instr("PRINT", None))
            elif i.op == "label":
                raw.append(Instr("LABEL", i.r))
            elif i.op == "goto":
                raw.append(Instr("JMP", i.r))
            elif i.op == "ifFalse":
                push(i.a)
                raw.append(Instr("JZ", i.r))
        raw.append(Instr("HALT", None))

        # resolve labels to instruction addresses
        addr, labels_at, n = {}, {}, 0
        for ins in raw:
            if ins.op == "LABEL":
                addr[ins.arg] = n
                labels_at.setdefault(n, []).append(ins.arg)
            else:
                n += 1
        program = []
        for ins in raw:
            if ins.op == "LABEL":
                continue
            program.append(Instr(ins.op, addr[ins.arg]) if ins.op in ("JMP", "JZ") else ins)
        return program, labels_at


def show_bytecode(program, labels_at) -> str:
    out = []
    for n, ins in enumerate(program):
        for lb in labels_at.get(n, []):
            out.append(f"      {lb}:")
        arg = "" if ins.arg is None else ins.arg
        note = ""
        if ins.op in ("JMP", "JZ"):
            note = "   ; -> " + ", ".join(labels_at.get(ins.arg, ["?"]))
        out.append(f"{n:4}    {ins.op:<6} {arg}{note}")
    return "\n".join(out)


# ============================================================================
# PHASE 7: RUNTIME - virtual machine
# ============================================================================
class VM:
    MAX_STEPS = 1_000_000

    def __init__(self, program, trace=False):
        self.program, self.trace = program, trace
        self.stack, self.mem, self.output = [], {}, []

    def run(self) -> List[int]:
        pc, steps = 0, 0
        while True:
            steps += 1
            if steps > self.MAX_STEPS:
                raise MiniLangRuntimeError("step limit exceeded (infinite loop?)")
            ins = self.program[pc]
            if self.trace:
                print(f"    pc={pc:<3} {ins.op:<6} {'' if ins.arg is None else ins.arg!s:<6} stack={self.stack}")
            pc += 1
            op = ins.op
            if op == "PUSH":
                self.stack.append(ins.arg)
            elif op == "LOAD":
                if ins.arg not in self.mem:
                    raise MiniLangRuntimeError(f"variable '{ins.arg}' read before assignment")
                self.stack.append(self.mem[ins.arg])
            elif op == "STORE":
                self.mem[ins.arg] = self.stack.pop()
            elif op in ARITH.values():
                b, a = self.stack.pop(), self.stack.pop()
                sym = next(k for k, v in ARITH.items() if v == op)
                if sym == "/" and b == 0:
                    raise MiniLangRuntimeError("division by zero")
                self.stack.append(eval_op(sym, a, b))
            elif op == "PRINT":
                v = self.stack.pop()
                self.output.append(v)
            elif op == "JMP":
                pc = ins.arg
            elif op == "JZ":
                if self.stack.pop() == 0:
                    pc = ins.arg
            elif op == "HALT":
                return self.output


# ============================================================================
# DRIVER: runs all phases and displays each one
# ============================================================================
def banner(title):
    print("\n" + "=" * 72)
    print(f" {title}")
    print("=" * 72)


def compile_and_run(source: str, optimize=True, trace=False) -> bool:
    banner("SOURCE CODE")
    for n, line in enumerate(source.rstrip().split("\n"), 1):
        print(f"{n:3} | {line}")

    try:
        # 1 - Lexer
        banner("PHASE 1: LEXICAL ANALYSIS  (tokens)")
        tokens = Lexer(source).tokenize()
        print(f"{'LINE:COL':<9} {'TYPE':<8} VALUE")
        for t in tokens:
            print(f"{t.line}:{t.col:<7} {t.type:<8} {t.value!r}")

        # 2 - Parser
        banner("PHASE 2: PARSING  (abstract syntax tree)")
        ast = Parser(tokens).parse()
        print(dump_ast(ast), end="")

        # 3 - Semantic analysis
        banner("PHASE 3: SEMANTIC ANALYSIS  (symbol table)")
        symbols = SemanticAnalyzer().analyze(ast)
        print(f"{'NAME':<8} {'UNIQUE':<8} {'TYPE':<6} {'SCOPE':<6} LINE")
        for name, uid, typ, depth, line in symbols:
            print(f"{name:<8} {uid:<8} {typ:<6} {depth:<6} {line}")
        print("\nNo semantic errors found.")

        # 4 - TAC
        banner("PHASE 4: INTERMEDIATE CODE  (three-address code)")
        tac = TACGenerator().generate(ast)
        print(show_tac(tac))

        # 5 - Optimizer
        banner("PHASE 5: OPTIMIZATION")
        if optimize:
            opt = Optimizer()
            optimized = opt.optimize(tac)
            print("Transformations applied:")
            for entry in opt.log or ["(none)"]:
                print("  *", entry)
            print(f"\nOptimized TAC  ({len(tac)} -> {len(optimized)} instructions):")
            print(show_tac(optimized))
            tac = optimized
        else:
            print("(skipped: --no-opt)")

        # 6 - Code generation
        banner("PHASE 6: TARGET CODE  (stack-machine bytecode)")
        program, labels_at = CodeGenerator().generate(tac)
        print(show_bytecode(program, labels_at))

        # 7 - Execution
        banner("PHASE 7: EXECUTION  (virtual machine)")
        vm = VM(program, trace)
        if trace:
            print("  trace:")
        output = vm.run()
        print("Program output:")
        for v in output:
            print(f"  {v}")
        if not output:
            print("  (no output)")
        print("\nFinal memory:", {k: v for k, v in vm.mem.items() if not k.startswith("t")})
        return True

    except MiniLangError as e:
        banner(f"COMPILATION STOPPED - {e.phase}")
        print(e)
        return False


SAMPLES = {
    "example": """\
let x = 10;
let y = 20;
let z = x + y * 2;
if (z > 40) {
    print z;
}
""",
    "factorial (while loop)": """\
// factorial of 5
let n = 5;
let f = 1;
while (n > 1) {
    f = f * n;
    n = n - 1;
}
print f;
""",
    "constant folding + if/else": """\
let k = (2 + 3) * 4 - 6 / 2;
let a = 7;
if (a != k) {
    print k;
} else {
    print 0;
}
""",
    "semantic errors": """\
let x = 5;
let x = 6;
y = 3;
print x + (x > 2);
if (x) { print 1; }
print 10 / 0;
""",
}


def main():
    ap = argparse.ArgumentParser(description="MiniLang compiler")
    ap.add_argument("file", nargs="?", help="MiniLang source file (default: built-in example)")
    ap.add_argument("--no-opt", action="store_true", help="skip the optimization phase")
    ap.add_argument("--trace", action="store_true", help="trace VM execution")
    ap.add_argument("--demo", action="store_true", help="run every built-in sample program")
    args = ap.parse_args()

    if args.demo:
        for name, src in SAMPLES.items():
            print("\n" + "#" * 72 + f"\n# SAMPLE: {name}\n" + "#" * 72)
            compile_and_run(src, not args.no_opt, args.trace)
        return 0
    if args.file:
        with open(args.file) as f:
            src = f.read()
    else:
        src = SAMPLES["example"]
    return 0 if compile_and_run(src, not args.no_opt, args.trace) else 1


if __name__ == "__main__":
    sys.exit(main())
