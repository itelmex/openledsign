"""Textos del esquematico sin encimarse: cajas de texto, obstaculos, colocacion automatica y revision.

Todo en mm de la hoja (Y hacia abajo). Una caja es (x0, y0, x1, y1).
Se usa desde gen_esquematico_cableado.py: primero se juntan los obstaculos fijos (cuerpos, pines con su numero,
cables, simbolos de alimentacion con su texto, etiquetas fijas, titulos de los marcos); despues se eligen las
etiquetas de red a media linea y al final la referencia y el valor de cada pieza, probando varias posiciones.
"""
from sexpr import find, find1

ANCHO_LETRA = 0.9      # ancho de cada letra / tamano de la letra (fuente de trazos de KiCad)


def ancho(texto, tam=1.27):
    return len(texto) * tam * ANCHO_LETRA


def caja_texto(texto, x, y, just=None, tam=1.27):
    """Caja de un texto horizontal con el ancla en (x, y), centrado en vertical."""
    w, h = ancho(texto, tam), tam * 1.1
    if just == 'left':
        x0 = x
    elif just == 'right':
        x0 = x - w
    else:
        x0 = x - w / 2
    return (x0, y - h / 2, x0 + w, y + h / 2)


def caja_etiqueta(texto, x, y, ang, tam=1.27):
    """Etiqueta local de KiCad: el texto queda encima del cable (justificado abajo)."""
    w, h = ancho(texto, tam), tam * 1.1
    if ang == 0:
        return (x + 0.3, y - h - 0.35, x + 0.3 + w, y - 0.35)
    if ang == 180:
        return (x - 0.3 - w, y - h - 0.35, x - 0.3, y - 0.35)
    if ang == 90:
        return (x - h - 0.35, y - 0.3 - w, x - 0.35, y - 0.3)
    return (x - h - 0.35, y + 0.3, x - 0.35, y + 0.3 + w)      # 270


def crece(c, m):
    return (c[0] - m, c[1] - m, c[2] + m, c[3] + m)


def area_cruce(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx * dy if dx > 0 and dy > 0 else 0.0


def linea(x0, y0, x1, y1, m=0.25):
    return (min(x0, x1) - m, min(y0, y1) - m, max(x0, x1) + m, max(y0, y1) + m)


def largos_pines(sym):
    """{numero: largo} de los pines del simbolo y si muestra los numeros."""
    out = {}
    for u in find(sym, 'symbol'):
        for p in find(u, 'pin'):
            out[find1(p, 'number')[1]] = float(find1(p, 'length')[1])
    numeros = not any(isinstance(x, list) and x and str(x[0]) == 'pin_numbers' and 'hide' in [str(y) for y in x] for x in sym)
    return out, numeros


class Mapa:
    """Obstaculos con nombre (para el reporte) y si son texto (pesan mas al encimarse)."""

    def __init__(self):
        self.items = []     # (caja, nombre, es_texto)

    def agrega(self, caja, nombre, texto=False):
        self.items.append((caja, nombre, texto))

    def costo(self, caja, ignora=()):
        c = 0.0
        for (b, n, t) in self.items:
            if n in ignora:
                continue
            a = area_cruce(caja, b)
            if a:
                c += a * (4.0 if t else 1.0) + 2.0
        return c

    def choques(self, caja, ignora=()):
        return [n for (b, n, t) in self.items if n not in ignora and area_cruce(caja, b) > 0.05]


def fuera(caja, marco):
    """Area de la caja fuera del marco (penaliza textos que se salen de su bloque)."""
    if not marco:
        return 0.0
    x0, y0, x1, y1 = marco
    w, h = caja[2] - caja[0], caja[3] - caja[1]
    dentro = area_cruce(caja, (x0 + 1.0, y0 + 7.0, x1 - 1.0, y1 - 1.0))
    return w * h - dentro


def opciones_pieza(ref, val, cuerpo, lados):
    """Posiciones candidatas para referencia y valor: (nombre, (xr, yr, xv, yv, just))."""
    bx0, bx1, by0, by1 = cuerpo
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    out = []
    for d in (0.0, 1.27, 2.54, 3.81):
        out += [
            ('derecha', (bx1 + 1.27 + d, cy - 1.27, bx1 + 1.27 + d, cy + 1.27, 'left')),
            ('izquierda', (bx0 - 1.27 - d, cy - 1.27, bx0 - 1.27 - d, cy + 1.27, 'right')),
            ('arriba-abajo', (cx, by0 - 1.9 - d, cx, by1 + 2.2 + d, None)),
            ('arriba', (cx, by0 - 4.4 - d, cx, by0 - 1.9 - d, None)),
            ('abajo', (cx, by1 + 2.2 + d, cx, by1 + 4.7 + d, None)),
            ('esquina', (bx1 + 1.27, by0 - 3.81 - d, bx1 + 1.27, by0 - 1.27 - d, 'left')),
            ('esquina-abajo', (bx1 + 1.27, by1 + 1.9 + d, bx1 + 1.27, by1 + 4.4 + d, 'left')),
            ('esquina-izq', (bx0 - 1.27, by0 - 3.81 - d, bx0 - 1.27, by0 - 1.27 - d, 'right')),
            ('esquina-izq-abajo', (bx0 - 1.27, by1 + 1.9 + d, bx0 - 1.27, by1 + 4.4 + d, 'right')),
            ('derecha-alta', (bx1 + 1.27 + d, by0 + 1.0, bx1 + 1.27 + d, by0 + 3.54, 'left')),
            ('derecha-baja', (bx1 + 1.27 + d, by1 - 3.54, bx1 + 1.27 + d, by1 - 1.0, 'left')),
            ('abajo-izq', (bx1, by0 - 1.9 - d, bx1, by1 + 2.2 + d, 'right')),
            ('abajo-der', (bx0, by0 - 1.9 - d, bx0, by1 + 2.2 + d, 'left')),
            ('esquina-alta', (bx1 + 1.27, by0 - 8.89 - d, bx1 + 1.27, by0 - 6.35 - d, 'left')),
        ]
    return out


def cajas_pieza(ref, val, pos):
    xr, yr, xv, yv, j = pos
    return caja_texto(ref, xr, yr, j), caja_texto(val, xv, yv, j)


def elegir(ref, val, cuerpo, lados, mapa, marco, preferida=None):
    """La posicion con menos choques; a igual costo gana la de la regla general (preferida) y las cercanas."""
    mejor = None
    for k, (nombre, pos) in enumerate(opciones_pieza(ref, val, cuerpo, lados)):
        a, b = cajas_pieza(ref, val, pos)
        c = mapa.costo(a) + mapa.costo(b) + 10 * (fuera(a, marco) + fuera(b, marco)) + area_cruce(a, b) * 8
        c += 0.05 * k + (0 if nombre == preferida else 0.3)
        if mejor is None or c < mejor[0]:
            mejor = (c, nombre, pos)
    return mejor
