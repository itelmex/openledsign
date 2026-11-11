"""Lector y escritor minimo de expresiones S de KiCad."""
import re

class Sym(str):
    """Atomo sin comillas (palabra clave o numero)."""

_tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')

def parse(text):
    stack = [[]]
    for m in _tok.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            e = stack.pop()
            stack[-1].append(e)
        elif t.startswith('"'):
            stack[-1].append(re.sub(r'\\(.)', lambda m: '\n' if m.group(1) == 'n' else m.group(1), t[1:-1]))
        else:
            stack[-1].append(Sym(t))
    return stack[0]

def fmt_atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, bool):
        return 'yes' if a else 'no'
    if isinstance(a, (int, float)):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    s = str(a).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return '"%s"' % s

def dump(e, ind=0):
    if not isinstance(e, list):
        return fmt_atom(e)
    if not any(isinstance(x, list) for x in e):
        return '(' + ' '.join(fmt_atom(x) for x in e) + ')'
    sp = '  ' * (ind + 1)
    head = []
    rest = []
    for x in e:
        if not rest and not isinstance(x, list):
            head.append(fmt_atom(x))
        else:
            rest.append(x)
    out = '(' + ' '.join(head)
    for x in rest:
        out += '\n' + sp + dump(x, ind + 1)
    return out + ')'

def find(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]

def find1(e, key):
    r = find(e, key)
    return r[0] if r else None
