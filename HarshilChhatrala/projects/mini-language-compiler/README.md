# MiniLang — Mini Programming Language Compiler

A small programming language implementation with a complete educational compiler pipeline and stack-machine virtual machine.

## Compiler pipeline

1. **Lexical analysis:** Converts source text into tokens and reports invalid characters.
2. **Parsing:** Uses recursive-descent parsing to build an Abstract Syntax Tree (AST).
3. **Semantic analysis:** Checks declaration-before-use, redeclaration, variable scopes, operand types, condition types, and constant division by zero.
4. **Intermediate code generation:** Produces Three-Address Code (TAC).
5. **Optimization:** Applies constant folding, constant propagation, algebraic simplification, branch folding, dead-store elimination, and control-flow cleanup.
6. **Target code generation:** Converts TAC into stack-machine bytecode.
7. **Runtime:** Executes bytecode using a custom virtual machine.

## Language features

- Integer variables using `let`
- Assignment and `print`
- Arithmetic: `+`, `-`, `*`, `/`
- Comparisons: `>`, `<`, `==`, `!=`
- `if` / `else` and `while`
- Nested blocks and `//` comments

## Requirements

Python 3.9+ (standard library only).

## Run

Run the built-in example:

```bash
python minilang.py
```

Run a source file:

```bash
python minilang.py examples/factorial.ml
```

Run all built-in demonstrations:

```bash
python minilang.py --demo
```

Disable optimization or trace virtual-machine execution:

```bash
python minilang.py examples/factorial.ml --no-opt
python minilang.py examples/factorial.ml --trace
```

## Example

Input (`examples/factorial.ml`):

```text
let n = 5;
let result = 1;
while (n > 1) {
    result = result * n;
    n = n - 1;
}
print result;
```

Expected program output:

```text
120
```

The compiler also prints tokens, the AST, symbol table, TAC, optimization steps, bytecode, and final VM memory.

## Scope and limitations

This is a teaching compiler for a deliberately small language. It uses integer variables and supports only the grammar documented in `minilang.py`. It is not a compiler for Python, C, or another general-purpose language.
