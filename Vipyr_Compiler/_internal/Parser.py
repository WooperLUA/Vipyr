import re
from pathlib import Path
import os

SUPERSCRIPT_MAP = {
    "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6",
    "⁷": "7", "⁸": "8", "⁹": "9"
}

CUSTOM_FUNCTIONS = {
    "vp.mapToList": "lambda lst, func: [func(x) for x in lst]",
    "vp.average": "lambda lst: sum(lst) / len(lst) if lst else 0",
    "vp.even": "lambda x: x % 2 == 0",
}

# List of keywords changed by the parser
SYNTAX_RULES = [

# Built-in functions
    #Generic
    (r"\b(" + "|".join(CUSTOM_FUNCTIONS.keys()) + r")\((.*?)\)",
     lambda m: f"({CUSTOM_FUNCTIONS[m.group(1)]})({m.group(2)})"),

    # mapToList handling
    (r"mapToList\((.*?)\s*,\s*(.*?)\)",
     lambda m: f"lambda lst, func: [func(x) for x in lst]({m.group(1)}, {m.group(2)})"),

#Fixes == -> @EQUALS@ (prevent converting == to =)
    (r"\s*==\s*", " @EQUALS@ "),
    # verbose (same as)
    (r"\s*same as\s*", " @EQUALS@ "),
    # verbose (equals)
    (r"\bequals\b", r"="),

# Classes:
    # this -> self
    (r"\bthis\b", "self"),

# Dictionary:
    # dict{"key"} → dict["key"]
    (r'(\w+(?:\{.*?\})+)', lambda m: re.sub(r'\{(.*?)\}', r'[\1]', m.group(1))),
    # key => value → key: value
    (r'(".*?")\s*=>\s*', r'\1: '),

# Variables:
    # type var = val -> var : type = val
    (r"\b(\w+)\s+(\w+)\s*=\s*(.+)", r"\2: \1 = \3"),
    # type[] var = [vals] -> var : list[type] = [vals]
    (r"\b(\w+)\[\]\s+(\w+)\s*=\s*(.+)", r"\2: list[\1] = \3"),

# Parameters:
    # param as type[] -> param: list[type]
    (r"\b(\w+)\s+as\s+(\w+)\[\]", r"\1: list[\2]"),
    # param as type -> param: type
    (r"\b(\w+)\s+as\s+(\w+)", r"\1: \2"),

    # param either type or type -> param : type | type
    (r"\b(\w+)\s+either\s+([\w\s]+)", lambda m: f"{m.group(1)}: {' | '.join(m.group(2).split(' or '))}"),


# Loops:
    # for i up to n -> for i in range(n)
    (r"\bfor\s+(\w+)\s+up to\s+(.+):", r"for \1 in range(\2):"),

# Functions:
    # get -> import
    (r"\bget\b", "import"),
    # named - > as
    (r"\bnamed\b", "as"),
    # function -> def
    (r"\bfunction (\w+)\((.*?)\)", r"def \1(\2)"),
    # throw -> raise
    (r"\bthrow\b", "raise"),
    # len() -> .length
    (r'(\w+)\.length', r'len(\1)'),
    # function type foo() -> def foo() -> type:
    (r"\bfunction\s+(\w+)(\[\])?\s+(\w+)\((.*?)\):",
     lambda m: f"def {m.group(3)}({m.group(4)}) -> {'list[' + m.group(1).lower() + ']' if m.group(2) else m.group(1).lower()}:"),


# Conditions:
    # switch -> match
    (r"\bswitch\b", "match"),
    # is type -> case type()
    (r"\bis\s+(\w+):", r"case \1():"),
    # default -> case _
    (r"\bdefault:", r"case _:"),
    # elsif -> elif
    (r"\belsif\b", "elif"),
    # unless -> if not
    (r"\bunless\b", "if not"),

#Operations:
    # ++ -> += 1
    (r"\b(\w+)\s*\+\+", r"\1 += 1"),
    # verbose (increment)
    (r"\b(\w+)\s*add", r"\1 += 1"),

    # -- -> -= 1
    (r"\b(\w+)\s*--", r"\1 -= 1"),
    # verbose (decrement)
    (r"\b(\w+)\s*sub", r"\1 -= 1"),

    # verbose (multiply -> *)
    (r"\bmultiply\b", r"*"),

    # x², y³, etc. -> x**2, y**3
    (r"(\w|\))([²³⁴⁵⁶⁷⁸⁹])", lambda m: f"{m.group(1)}**{SUPERSCRIPT_MAP[m.group(2)]}"),

# Types:
    # string -> str
    (r"\bstring\b", "str"),
    # boolean -> bool
    (r"\bboolean\b", "bool"),
    # double -> float
    (r"\bdouble\b", "float"),

# Boolean values:
    # true -> True
    (r"\btrue\b", "True"),
    # false -> False
    (r"\bfalse\b", "False"),
    # null -> None
    (r"\bnull\b", "None"),

# Terminal:
    (r"\bprint\.(log|warn|debug)\s*\((.*?)\)", r'print("\1 : " + str(\2))'),

# Other:
    # // -> #
    (r"//(.*)", r"# \1"),
    # /* */ -> ''' or """
    (r"/\*\s*(.*?)\s*\*/", r'"""\1"""'),

# Fixes @EQUALS@ -> == (prevent converting == to =)
    (r" @EQUALS@ ", " == ")
]



# This translates the code into native python
def preprocess(code, way):
    match (way):
        case "vp->py":
            for pattern, replacement in SYNTAX_RULES:
                code = re.sub(pattern, replacement, code)
        case "py->vp":
            for pattern, replacement in SYNTAX_RULES:
                code = re.sub(replacement, pattern, code)

    return code

'''
    Compiles the code into native Python code as compiled_filename.
    File is created in the dir where the compile method is called.
'''
def compile_custom_code(custom_code, way):
    content = ""
    with open(custom_code, "r", encoding="utf-8") as file:
        content = file.read()
    python_code = preprocess(content, way)
    file_name = ""
    if way == "vp->py":
        file_name = "compiled_" + Path(custom_code).stem + ".py"
    elif way == "py->vp":
        file_name = "compiled_" + Path(custom_code).stem + ".vp"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(python_code)
    os.replace(file_name, os.path.basename(file_name))

'''
    Compiles than executes the code into a native Python code.
    No file is created.
'''
def execute_custom_code(custom_code):
    content = ""
    with open(custom_code, "r", encoding="utf-8") as file:
        content = file.read()
    python_code = preprocess(content, "vp->py")
    exec(python_code, globals())