"""Carga simbolos de las librerias de KiCad, resuelve 'extends' y lista los pines."""
import copy, os
from sexpr import parse, find, find1, Sym

LIBDIR = '/usr/share/kicad/symbols'
_cache = {}

def _lib(name, path=None):
    if name not in _cache:
        p = path or os.path.join(LIBDIR, name + '.kicad_sym')
        _cache[name] = {s[1]: s for s in find(parse(open(p).read())[0], 'symbol')}
    return _cache[name]

def get(libid, path=None):
    """Simbolo aplanado con nombre 'Lib:Nombre' listo para lib_symbols."""
    lib, name = libid.split(':')
    syms = _lib(lib, path)
    s = copy.deepcopy(syms[name])
    ext = find1(s, 'extends')
    if ext:
        base = get(lib + ':' + ext[1], path)
        b = copy.deepcopy(base)
        basename = base[1].split(':')[1]
        # propiedades del derivado reemplazan a las de la base
        props = {p[1]: p for p in find(s, 'property')}
        b2 = [b[0], libid]
        for x in b[2:]:
            if isinstance(x, list) and x and x[0] == 'property' and x[1] in props:
                b2.append(props.pop(x[1]))
            elif isinstance(x, list) and x and x[0] == 'symbol':
                x = copy.deepcopy(x)
                x[1] = x[1].replace(basename, name, 1)
                b2.append(x)
            else:
                b2.append(x)
        for p in props.values():
            b2.insert(2, p)
        return b2
    s[1] = libid
    return s

def pins(sym):
    """[(unidad, numero, nombre, x, y, angulo, tipo)] en coordenadas del simbolo (Y hacia arriba)."""
    name = sym[1].split(':')[1]
    out = []
    for u in find(sym, 'symbol'):
        suf = u[1][len(name) + 1:]
        unit = int(suf.split('_')[0])
        for p in find(u, 'pin'):
            at = find1(p, 'at')
            nm = find1(p, 'name')[1]
            num = find1(p, 'number')[1]
            out.append((unit, num, nm, float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0, str(p[1])))
    return out

def units(sym):
    return sorted({p[0] for p in pins(sym) if p[0] > 0}) or [1]
