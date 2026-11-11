"""Esquematico de UNA hoja con cables reales (sin etiquetas que van y vienen).

Las piezas se acomodan por bloques; cada pieza chica junto al chip con el que comparte mas redes. Un ruteador de
rejilla (A*) traza los cables en angulo recto sin encimar redes distintas: solo se cruzan en perpendicular (sin
punto de union). Las redes de alimentacion (GND, +3V3, +5V3, +VIN...) usan simbolos de alimentacion.

Escribe ../tarjeta_openled_s3.kicad_sch (hoja unica). Despues hay que correr enlazar_pcb.py para que la PCB
apunte a los simbolos nuevos sin perder el ruteo.
"""
import copy, heapq, os, uuid, datetime
from sexpr import Sym as S, dump, find, find1
import libsym, diseno, gen_esquematico as GE

SALIDA = GE.SALIDA
PROYECTO = GE.PROYECTO
G = 1.27                      # rejilla del ruteador (mm)
PAPEL, ANCHO_HOJA, ALTO_HOJA = getattr(diseno, 'HOJA', ('A0', 1189.0, 841.0))
POTENCIA = getattr(diseno, 'POTENCIA', {'GND': 'power:GND', '+3V3': 'power:+3V3', '+5V': 'power:+5V',
            '+VIN': None, '+VSENS': None, '+5V_DK': None, '+LOOP1': None, '+LOOP2': None})
ANCLAS = ('U', 'J', 'K', 'BZ', 'SW', 'BT', 'L', 'H')

def U():
    return str(uuid.uuid4())

def gi(v):
    return int(round(v / G))

# ============================================================
#  Simbolos de alimentacion propios (el nombre del pin es el nombre de la red)
# ============================================================
def simbolo_potencia(red):
    if POTENCIA[red]:
        return POTENCIA[red], libsym.get(POTENCIA[red])
    base = libsym.get('power:+5V')
    nombre = 'PWR_' + red
    s = copy.deepcopy(base)
    s[1] = 'openled:' + nombre
    for x in s:
        if isinstance(x, list) and x and x[0] == 'property' and x[1] == 'Value':
            x[2] = red
        if isinstance(x, list) and x and x[0] == 'symbol':
            x[1] = x[1].replace('+5V', nombre, 1)
            for p in find(x, 'pin'):
                find1(p, 'name')[1] = red
    return 'openled:' + nombre, s

# ============================================================
#  Instancias (pieza, unidad) y medidas
# ============================================================
def cuerpo(sym):
    xs, ys = [], []
    def rec(e):
        if isinstance(e, list) and e:
            if e[0] == 'pin':
                return
            if e[0] in ('xy', 'start', 'end') and len(e) >= 3:
                xs.append(float(e[1])); ys.append(float(e[2]))
            if e[0] == 'circle':
                c = find1(e, 'center'); r = float(find1(e, 'radius')[1])
                xs.extend([float(c[1]) - r, float(c[1]) + r]); ys.extend([float(c[2]) - r, float(c[2]) + r])
            for x in e[1:]:
                rec(x)
    for u in find(sym, 'symbol'):
        rec(u)
    if not xs:
        return -1.27, 1.27, -1.27, 1.27
    return min(xs), max(xs), min(ys), max(ys)

class Inst:
    def __init__(self, p, unidad, sym, ps):
        self.p, self.unidad, self.sym, self.ps = p, unidad, sym, ps
        self.ref = p['ref']
        x0, x1, y0, y1 = GE.caja(sym)              # con pines
        self.caja = (x0, x1, y0, y1)
        self.redes = {p['pins'].get(n) for (_, n, *_r) in ps} - {None}
        self.x = self.y = 0.0
        self.rot, self.esp = 0, None     # rotacion (grados, contra reloj) y espejo ('x', 'y' o None)

    def ancho(self):
        x0, x1, y0, y1 = self.caja
        extra = 1.27 * 1.1 * max(len(self.ref), len(self.p['value'])) if GE.angosto(self.sym) else 0
        return (x1 - x0) + extra + 5.08

    def alto(self):
        x0, x1, y0, y1 = self.caja
        return (y1 - y0) + (5.08 if GE.angosto(self.sym) else 10.16)

def instancias():
    out = []
    for p in diseno.partes:
        sym = GE.cargar_simbolo(p['sym'])
        allp = libsym.pins(sym)
        for un in (p['unidades'] or [1]):
            out.append(Inst(p, un, sym, [x for x in allp if x[0] in (0, un)]))
    return out

def es_ancla(i):
    return i.ref.rstrip('0123456789') in ANCLAS

def tr(i, x, y):
    """Punto del simbolo (Y hacia arriba) -> desplazamiento en la hoja (Y hacia abajo), con espejo y rotacion."""
    if i.esp == 'y':
        x = -x
    elif i.esp == 'x':
        y = -y
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[i.rot % 360]
    return x * c - y * s, -(x * s + y * c)

def pin_hoja(i, px, py, a):
    """Extremo del pin en la hoja y direccion hacia afuera del simbolo."""
    sx, sy = tr(i, px, py)
    bx, by = tr(i, *{0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[a % 360])   # hacia el cuerpo
    return i.x + sx, i.y + sy, (-int(round(bx)), -int(round(by)))

def caja_hoja(i, caja):
    x0, x1, y0, y1 = caja
    pts = [tr(i, x, y) for x in (x0, x1) for y in (y0, y1)]
    return (i.x + min(p[0] for p in pts), i.x + max(p[0] for p in pts),
            i.y + min(p[1] for p in pts), i.y + max(p[1] for p in pts))

# ============================================================
#  Colocacion por bloques y grupos
# ============================================================
def agrupar(insts):
    senal = lambda i: {r for r in i.redes if r not in POTENCIA}
    anclas = [i for i in insts if es_ancla(i)]
    grupo = {}
    for i in insts:
        if es_ancla(i) or i.ref.startswith('#'):
            continue
        mejor, pts = None, (0, 0)
        for a in anclas:
            n = len(senal(i) & senal(a))
            if n and (n, -len(a.ps)) > pts:
                mejor, pts = a, (n, -len(a.ps))
        if mejor:
            grupo[id(i)] = mejor
    # segunda vuelta: piezas que solo tocan otra pieza chica
    for _ in range(2):
        for i in insts:
            if es_ancla(i) or i.ref.startswith('#') or id(i) in grupo:
                continue
            for j in insts:
                if id(j) in grupo and senal(i) & senal(j):
                    grupo[id(i)] = grupo[id(j)]; break
    clusters = {id(a): [a] for a in anclas}
    sueltas = []
    for i in insts:
        if es_ancla(i):
            continue
        if id(i) in grupo:
            clusters[id(grupo[id(i)])].append(i)
        else:
            sueltas.append(i)
    lista = [c for c in clusters.values()]
    if sueltas:
        lista.append(sueltas)
    return lista

def acomodar_cluster(c):
    """Ancla a la izquierda; las demas piezas en renglones a su derecha. Devuelve (ancho, alto)."""
    a = c[0]
    a.dx, a.dy = 0.0, 0.0
    x0 = a.ancho() + 7.62
    x, y, fila, anchomax = x0, 0.0, 0.0, x0
    LIM = x0 + 70
    for i in c[1:]:
        w, h = i.ancho(), i.alto()
        if x > x0 and x + w > LIM:
            x, y, fila = x0, y + fila + 5.08, 0.0
        i.dx, i.dy = x, y
        x += w + 7.62
        fila = max(fila, h)
        anchomax = max(anchomax, x)
    return anchomax, max(a.alto(), y + fila)

TEXTO = {}   # ref -> donde va su referencia y valor (lo puede indicar la plantilla)
PUERTOS = {}   # red -> (x, y, hacia): salida explicita del bloque, la linea termina en la etiqueta
COLUMNAS = getattr(diseno, 'COLUMNAS', [[h] for h, _ in diseno.HOJAS])

def colocar(insts):
    if getattr(diseno, 'PLANTILLA', None):     # acomodo a mano: plantilla_<tarjeta>.py
        import importlib
        mod = importlib.import_module(diseno.PLANTILLA)
        pos = mod.plantilla()
        faltan = [i.ref for i in insts if i.ref not in pos]
        if faltan:
            raise SystemExit('la plantilla no acomoda: ' + ' '.join(faltan))
        for i in insts:
            x, y, i.rot, i.esp = pos[i.ref]
            i.x, i.y = round(round(x / G) * G, 4), round(round(y / G) * G, 4)
        TEXTO.update(getattr(mod, 'TEXTO', {}))
        PUERTOS.update(getattr(mod, 'PUERTOS', {}))
        return [('marco',) + m for m in mod.MARCOS]
    titulo_de = dict(diseno.HOJAS)
    titulos = []
    X0, Y0, MARGEN = 30.48, 40.64, 20.32
    ANCHO_COL = (ANCHO_HOJA - 2 * X0 - (len(COLUMNAS) - 1) * 25.4) / len(COLUMNAS)
    for k, col in enumerate(COLUMNAS):
        bx, by = X0 + k * (ANCHO_COL + 25.4), Y0
        for nombre in col:
            bi = [i for i in insts if i.p['hoja'] == nombre]
            cl = agrupar(bi)
            cl.sort(key=lambda c: (-len(c[0].ps), c[0].ref))
            x, y, fila = 0.0, 12.7, 0.0
            pos = []
            for c in cl:
                w, h = acomodar_cluster(c)
                if x > 0 and x + w > ANCHO_COL:
                    x, y, fila = 0.0, y + fila + 15.24, 0.0
                pos.append((c, x, y))
                x += w + 15.24
                fila = max(fila, h)
            for c, cx, cy in pos:
                for i in c:
                    x0, x1, y0, y1 = i.caja
                    i.x = round(round((bx + cx + i.dx - x0) / 2.54) * 2.54, 4)
                    i.y = round(round((by + cy + i.dy + y1 + 5.08) / 2.54) * 2.54, 4)
            titulos.append((titulo_de[nombre], bx, by))
            by += y + fila + MARGEN + 12.7
        if by > ALTO_HOJA - 30:
            print('AVISO: la columna %d se pasa de la hoja (%.0f mm)' % (k + 1, by))
    return titulos

# ============================================================
#  Ruteador de rejilla
# ============================================================
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

class Rejilla:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.bloq = bytearray(w * h)
        self.Hn = [0] * (w * h)       # red que usa la celda en horizontal
        self.Vn = [0] * (w * h)
        self.nodo = [0] * (w * h)     # celda que es extremo/esquina/union/pin de una red (exclusiva)
        self.aristas = {}             # (celda, celda) -> red

    def i(self, x, y):
        return y * self.w + x

    def libre_para(self, c, red):
        return self.nodo[c] in (0, red) and self.Hn[c] in (0, red) and self.Vn[c] in (0, red)

def rutear(insts, rej, redes_pines, ids):
    w, h = rej.w, rej.h
    fallidas = []
    nid = lambda r: ids[r]
    # orden: redes chicas primero
    orden = sorted(redes_pines.items(), key=lambda kv: (len(kv[1]), (max(p[0] for p in kv[1]) - min(p[0] for p in kv[1])) +
                                                     (max(p[1] for p in kv[1]) - min(p[1] for p in kv[1]))))
    segs = []
    for red, pines in orden:
        n = nid(red)
        terms = [(x, y) for (x, y, d) in pines]
        arbol = {terms[0]}
        pend = terms[1:]
        while pend:
            # el terminal pendiente mas cercano al arbol
            pend.sort(key=lambda t: min(abs(t[0] - a[0]) + abs(t[1] - a[1]) for a in arbol))
            t = pend.pop(0)
            camino = None
            for margen in (25, 80, 400):
                xs = [p[0] for p in arbol] + [t[0]]; ys = [p[1] for p in arbol] + [t[1]]
                caja = (max(0, min(xs) - margen), max(0, min(ys) - margen), min(w - 1, max(xs) + margen), min(h - 1, max(ys) + margen))
                camino = astar(rej, t, arbol, n, caja)
                if camino:
                    break
            if not camino:
                fallidas.append((red, t))
                continue
            marcar(rej, camino, n)
            arbol.update(camino)
            segs.append((red, camino))
    return segs, fallidas, ids

def astar(rej, ini, arbol, n, caja):
    w = rej.w
    x0, y0, x1, y1 = caja
    meta = {rej.i(*a) for a in arbol if rej.libre_para(rej.i(*a), n)}
    if not meta:
        return None
    mx = [a[0] for a in arbol]; my = [a[1] for a in arbol]
    def hfun(x, y):
        return min(abs(x - a) + abs(y - b) for a, b in zip(mx[:40], my[:40]))
    c0 = rej.i(*ini)
    abiertos = [(0, 0, ini[0], ini[1], -1)]
    costo = {(c0, -1): 0}
    padre = {}
    BEND, CRUCE = 4, 6
    exp = 0
    while abiertos:
        f, g, x, y, d = heapq.heappop(abiertos)
        c = y * w + x
        if c in meta and (x, y) != ini:
            # reconstruir
            cam = [(x, y)]
            k = (c, d)
            while k in padre:
                k = padre[k]
                cam.append((k[0] % w, k[0] // w))
            return cam[::-1]
        exp += 1
        if exp > 400000:
            return None
        for nd, (dx, dy) in enumerate(DIRS):
            if d >= 0 and (dx, dy) == (-DIRS[d][0], -DIRS[d][1]):
                continue
            nx, ny = x + dx, y + dy
            if nx < x0 or ny < y0 or nx > x1 or ny > y1:
                continue
            cn = ny * w + nx
            # dar vuelta en c: c no puede tener otras redes
            if d >= 0 and nd != d and not rej.libre_para(c, n):
                continue
            if rej.bloq[cn] and cn not in meta:
                continue
            if rej.nodo[cn] not in (0, n):
                continue
            hor = dy == 0
            if hor and rej.Hn[cn] not in (0, n):
                continue
            if not hor and rej.Vn[cn] not in (0, n):
                continue
            # no recorrer en paralelo pegado a un pin de otra red (seria conexion por extremo)
            ng = g + 1 + (BEND if d >= 0 and nd != d else 0)
            otro = rej.Vn[cn] if hor else rej.Hn[cn]
            if otro not in (0, n):
                if cn in meta:
                    continue
                ng += CRUCE
            k = (cn, nd)
            if ng < costo.get(k, 1 << 30):
                costo[k] = ng
                padre[k] = (c, d)
                heapq.heappush(abiertos, (ng + hfun(nx, ny), ng, nx, ny, nd))
    return None

def marcar(rej, cam, n):
    w = rej.w
    for k, (x, y) in enumerate(cam):
        c = y * w + x
        dirs = set()
        if k > 0:
            dirs.add('h' if cam[k - 1][1] == y else 'v')
        if k < len(cam) - 1:
            dirs.add('h' if cam[k + 1][1] == y else 'v')
        if 'h' in dirs:
            rej.Hn[c] = n
        if 'v' in dirs:
            rej.Vn[c] = n
        extremo = k == 0 or k == len(cam) - 1
        esquina = len(dirs) == 2
        if extremo or esquina:
            rej.nodo[c] = n
        if k > 0:
            a = rej.i(*cam[k - 1])
            rej.aristas[(min(a, c), max(a, c))] = n

def a_segmentos(cam):
    out = []
    ini = cam[0]
    for k in range(1, len(cam)):
        if k == len(cam) - 1 or (cam[k + 1][0] - cam[k][0], cam[k + 1][1] - cam[k][1]) != (cam[k][0] - cam[k - 1][0], cam[k][1] - cam[k - 1][1]):
            out.append((ini, cam[k]))
            ini = cam[k]
    return out

# ============================================================
def generar():
    GE.escribir_libreria()
    insts = instancias()
    titulos = colocar(insts)
    W, H = gi(ANCHO_HOJA), gi(ALTO_HOJA)
    rej = Rejilla(W, H)

    def bloquear(gx, gy):
        if 0 <= gx < W and 0 <= gy < H:
            rej.bloq[rej.i(gx, gy)] = 1
    # obstaculos: cuerpos y pines
    potencia_pines = []
    redes_pines = {}
    for i in insts:
        x0, x1, y0, y1 = caja_hoja(i, cuerpo(i.sym))
        for gx in range(gi(x0), gi(x1) + 1):
            for gy in range(gi(y0), gi(y1) + 1):
                bloquear(gx, gy)
    import textos as _TX
    for i in insts:
        largos, _n = _TX.largos_pines(i.sym)
        for (_, num, _, px, py, a, _) in i.ps:
            sx, sy, (dx, dy) = pin_hoja(i, px, py, a)
            for k in range(1, max(1, int(round(largos.get(num, 2.54) / G))) + 1):
                bloquear(gi(sx) - dx * k, gi(sy) - dy * k)
    # redes que llegan a la ESP32: en su pin solo un tramo corto con etiqueta (mismo nombre en el bloque)
    ESP = getattr(diseno, 'ETIQUETAR_EN', None)
    # OpenLed: redes que llevan etiqueta en cada pin (buses que se reparten a varios conectores) y pines sueltos con etiqueta
    ETIQ_REDES = set(getattr(diseno, 'ETIQUETAR_REDES', ()))
    ETIQ_PINES = set(getattr(diseno, 'ETIQUETAR_PINES', ()))
    LARGO_ETQ = dict(getattr(diseno, 'LARGO_ETIQUETA', {}))   # (ref, pin) -> celdas del tramo (para librar un simbolo vecino)
    largo_etq = {}
    etiquetas = []      # (x, y, dx, dy, red) en celdas: extremo del tramo
    for i in insts:
        for (_, num, _, px, py, a, _) in i.ps:
            sx, sy, (dx, dy) = pin_hoja(i, px, py, a)
            ex, ey = gi(sx), gi(sy)
            red = i.p['pins'].get(num)
            c = rej.i(ex, ey)
            rej.bloq[c] = 0
            for k in (1, 2):   # la salida del pin siempre libre
                rej.bloq[rej.i(ex + dx * k, ey + dy * k)] = 0
            if red is None:
                rej.nodo[c] = -1
                continue
            if red in POTENCIA:
                potencia_pines.append((i, num, ex, ey, dx, dy, red))
            elif (ESP and i.ref == ESP) or red in ETIQ_REDES or (i.ref, num) in ETIQ_PINES:
                etiquetas.append((ex, ey, dx, dy, red))
                if (i.ref, num) in LARGO_ETQ:
                    largo_etq[(ex, ey)] = LARGO_ETQ[(i.ref, num)]
            else:
                redes_pines.setdefault(red, []).append((ex, ey, (dx, dy)))
    # puertos: un extremo mas de la red, en la orilla del bloque, con su etiqueta
    HACIA = {'der': (1, 0), 'izq': (-1, 0), 'arriba': (0, -1), 'abajo': (0, 1)}
    puertos, tramos_puerto = [], []
    for red, (x, y, hacia) in PUERTOS.items():
        dx, dy = HACIA[hacia]
        ex, ey = gi(x), gi(y)
        # el cable llega por un tramo recto fijo en la direccion de la etiqueta
        tx, ty = ex - 2 * dx, ey - 2 * dy
        redes_pines.setdefault(red, []).append((tx, ty, (dx, dy)))
        rej.bloq[rej.i(tx, ty)] = 0
        for k in (1, 2):
            c = rej.i(tx + dx * k, ty + dy * k)
            rej.nodo[c] = -2; rej.bloq[c] = 1
        tramos_puerto.append((tx, ty, ex, ey))
        largo = gi(len(red) * 1.15) + 2      # el texto de la etiqueta no se cruza
        for k in range(1, largo):
            for o in (-1, 0, 1):
                bloquear(ex + dx * k + (o if dy else 0), ey + dy * k + (o if dx else 0))
        puertos.append((ex, ey, dx, dy, red))
    # redes con un solo pin fuera de la ESP32: tambien con etiqueta en el pin
    for red, ps in list(redes_pines.items()):
        if len(ps) == 1 and any(r == red for *_x, r in etiquetas):
            ex, ey, (dx, dy) = ps[0]
            etiquetas.append((ex, ey, dx, dy, red))
            del redes_pines[red]
    tramos_etq = []
    for (ex, ey, dx, dy, red) in etiquetas:
        L = largo_etq.get((ex, ey), 2)
        for k in range(0, L + 1):
            c = rej.i(ex + dx * k, ey + dy * k)
            rej.nodo[c] = -2; rej.bloq[c] = 1
        largo = gi(len(red) * 1.15) + 2      # el texto de la etiqueta tampoco se cruza
        for k in range(L, L + largo):
            for o in (-1, 0, 1):
                bloquear(ex + dx * k + (o if dy else 0), ey + dy * k + (o if dx else 0))
        tramos_etq.append((ex, ey, ex + dx * L, ey + dy * L, dx, dy, red))
    # simbolos de alimentacion: un tramo hacia afuera y el simbolo; pines vecinos con tramos escalonados
    grupos = {}
    for t in potencia_pines:
        i, num, ex, ey, dx, dy, red = t
        grupos.setdefault((id(i), dx, dy), []).append(t)
    largo_pot, derecho = {}, {}
    sin_simbolo, puentes_pot = set(), []
    ocup_pines = {}
    for i in insts:
        for (_, num, _, px, py, a, _) in i.ps:
            sx, sy, d = pin_hoja(i, px, py, a)
            ocup_pines.setdefault((id(i), d), set()).add((gi(sx), gi(sy)))
    for (_, dx, dy), ts in grupos.items():
        ts.sort(key=lambda t: (t[3], t[2]) if dx else (t[2], t[3]))
        racimos, previo = [], None
        for t in ts:
            p = t[3] if dx else t[2]
            if previo is not None and abs(p - previo) <= 2:
                racimos[-1].append(t)
            else:
                racimos.append([t])
            previo = p
        for r in racimos:
            misma = len(r) > 1 and len({t[6] for t in r}) == 1
            for k, t in enumerate(r):
                largo_pot[id(t)] = 2 if misma else 2 + 3 * k
                if misma and k:         # pines vecinos de la misma red: una linea entre ellos y un solo simbolo
                    sin_simbolo.add(id(t))
                    puentes_pot.append((r[0][2] + dx * 2, r[0][3] + dy * 2, t[2] + dx * 2, t[3] + dy * 2))
                # un pin solo que sale de lado: el simbolo queda derecho (+V arriba, GND abajo)
                vec = ocup_pines.get((id(t[0]), (dx, dy)), set())
                solo = not any((t[2], t[3] + o) in vec for o in (-2, -1, 1, 2))
                derecho[id(t)] = dx != 0 and len(r) == 1 and solo
    pot_items = []
    for t in potencia_pines:
        (i, num, ex, ey, dx, dy, red) = t
        L = largo_pot[id(t)]
        for k in range(0, L + 1):
            c = rej.i(ex + dx * k, ey + dy * k)
            rej.nodo[c] = -2
            rej.bloq[c] = 1
        fx, fy = ex + dx * L, ey + dy * L
        if id(t) in sin_simbolo:
            pot_items.append((ex, ey, fx, fy, dx, dy, red, None))
            continue
        if derecho[id(t)]:
            sy = 1 if red == 'GND' else -1
            for ox in (-1, 0, 1):          # el simbolo y su texto (+V arriba de la flecha, GND abajo)
                for oy in (1, 2, 3, 4):
                    bloquear(fx + ox, fy + sy * oy)
        else:              # el simbolo y su texto hacia afuera del pin
            for k in range(1, 5 + (gi(len(red) * 1.15) + 1 if dx else 0)):
                for o in (-1, 0, 1):
                    bloquear(fx + dx * k + (o if dy else 0), fy + dy * k + (o if dx else 0))
        pot_items.append((ex, ey, fx, fy, dx, dy, red, derecho[id(t)]))
    for (x0, y0, x1, y1) in puentes_pot:
        for gx in range(min(x0, x1), max(x0, x1) + 1):
            for gy in range(min(y0, y1), max(y0, y1) + 1):
                rej.nodo[rej.i(gx, gy)] = -2; rej.bloq[rej.i(gx, gy)] = 1
    # los extremos de pin pertenecen a su red: ningun cable de otra red puede pasar por ahi
    ids = {r: k + 1 for k, r in enumerate(sorted(set(redes_pines) | {e[4] for e in etiquetas}))}
    for red, ps in redes_pines.items():
        for (ex, ey, d) in ps:
            rej.nodo[rej.i(ex, ey)] = ids[red]
    segs, fallidas, ids = rutear(insts, rej, {r: ps for r, ps in redes_pines.items() if len(ps) > 1}, ids)

    # ---------- textos sin encimarse: obstaculos fijos, etiquetas a media linea y texto de cada pieza
    import textos as TX
    mapa = TX.Mapa()
    marcos = [t[2:] for t in titulos if t[0] == 'marco']

    def marco_de(x, y):
        for m in marcos:
            if m[0] <= x <= m[2] and m[1] <= y <= m[3]:
                return m
        return None
    for t in titulos:
        if t[0] == 'marco':
            mapa.agrega(TX.caja_texto(t[1].upper(), t[2] + 2.54, t[3] + 4.45, 'left', 2.0), 'titulo ' + t[1], True)
    for i in insts:
        cb = caja_hoja(i, cuerpo(i.sym))
        mapa.agrega(TX.crece((cb[0], cb[2], cb[1], cb[3]), 0.2), 'cuerpo ' + i.ref)
        largos, numeros = TX.largos_pines(i.sym)
        for (_, num, _, px, py, a, _) in i.ps:
            sx, sy, (dx, dy) = pin_hoja(i, px, py, a)
            L = largos.get(num, 2.54)
            mapa.agrega(TX.linea(sx, sy, sx - dx * L, sy - dy * L, 1.3 if numeros else 0.3), 'pin %s.%s' % (i.ref, num))
            if i.p['pins'].get(num) is None:
                mapa.agrega(TX.crece((sx, sy, sx, sy), 0.9), 'nc %s.%s' % (i.ref, num))

    def cable(a, b, nombre):
        mapa.agrega(TX.linea(a[0] * G, a[1] * G, b[0] * G, b[1] * G), nombre)
    for red, cam in segs:
        for (a, b) in a_segmentos(cam):
            cable(a, b, 'cable ' + red)
    for (ex, ey, fx, fy, dx, dy, red) in tramos_etq:
        cable((ex, ey), (fx, fy), 'cable ' + red)
    for (tx, ty, ex, ey) in tramos_puerto:
        cable((tx, ty), (ex, ey), 'cable puerto')
    pot_dibujo = []
    for (x0, y0, x1, y1) in puentes_pot:
        cable((x0, y0), (x1, y1), 'cable puente')
    for (ex, ey, fx, fy, dx, dy, red, der) in pot_items:
        if der is None:      # pin que comparte el simbolo de su vecino
            pot_dibujo.append((ex, ey, fx, fy, None, 0, 0, None, red))
            cable((ex, ey), (fx, fy), 'cable ' + red)
            continue
        abajo = red == 'GND'
        # el cuerpo del simbolo hacia afuera del pin (o derecho si el pin va solo)
        if der:
            rot = 0
        elif abajo:
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[(dx, dy)]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[(dx, dy)]
        sale = (0, 1 if abajo else -1) if der else (dx, dy)
        if sale[0] == 0:   # texto junto al simbolo, horizontal
            vx, vy, just = fx * G, fy * G + sale[1] * (5.08 if abajo else 3.81), None
        else:
            vx, vy, just = fx * G + dx * 4.0, fy * G, 'left' if dx > 0 else 'right'
        pot_dibujo.append((ex, ey, fx, fy, rot, vx, vy, just, red))
        cable((ex, ey), (fx, fy), 'cable ' + red)
        X, Y = fx * G, fy * G
        if sale[0] == 0:
            mapa.agrega((X - 1.4, min(Y, Y + sale[1] * 2.8), X + 1.4, max(Y, Y + sale[1] * 2.8)), 'simbolo %s@%.0f,%.0f' % (red, X, Y))
        else:
            mapa.agrega((min(X, X + sale[0] * 2.8), Y - 1.4, max(X, X + sale[0] * 2.8), Y + 1.4), 'simbolo %s@%.0f,%.0f' % (red, X, Y))
        mapa.agrega(TX.caja_texto(red, GE.g(vx), GE.g(vy), just), 'texto %s@%.0f,%.0f' % (red, X, Y), True)
    ANG_ETQ = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}

    def caja_etq(red, x, y, dx, dy, tam=1.27):
        return TX.caja_etiqueta(red, x * G, y * G, ANG_ETQ[(dx, dy)], tam)
    for (ex, ey, fx, fy, dx, dy, red) in tramos_etq:
        mapa.agrega(caja_etq(red, fx, fy, dx, dy), 'etiqueta ' + red, True)
    for (ex, ey, dx, dy, red) in puertos:
        mapa.agrega(caja_etq(red, ex, ey, dx, dy), 'etiqueta ' + red, True)
    # etiquetas a media linea: el punto de la red donde su texto no choca con nada
    etq_medias = []
    con_etq = {e[4] for e in etiquetas}
    por_red = {}
    for red, cam in segs:
        por_red.setdefault(red, []).extend(a_segmentos(cam))
    for red, ss in sorted(por_red.items()):
        if red in PUERTOS:
            continue
        n = ids[red]
        tam = 1.27 if red in con_etq else 1.0
        mejor_c = None
        for (p, q) in ss:
            L = abs(p[0] - q[0]) + abs(p[1] - q[1])
            if L < 2:
                continue
            dx = (q[0] > p[0]) - (q[0] < p[0]); dy = (q[1] > p[1]) - (q[1] < p[1])
            if dx < 0 or dy > 0:       # texto de izquierda a derecha / de abajo hacia arriba
                p, q, dx, dy = q, p, -dx, -dy
            for k in range(1, L):
                x, y = p[0] + dx * k, p[1] + dy * k
                c = rej.i(x, y)
                if not (rej.Hn[c] in (0, n) and rej.Vn[c] in (0, n) and rej.nodo[c] in (0, n)):
                    continue
                caja = caja_etq(red, x, y, dx, dy, tam)
                costo = mapa.costo(caja, ignora=('cable ' + red,)) + 0.02 * abs(k - L / 2) + (0.5 if dy else 0)
                if mejor_c is None or costo < mejor_c[0]:
                    mejor_c = (costo, x, y, dx, dy, caja)
        # una red interna sin lugar limpio se queda sin etiqueta (KiCad le pone nombre); las que van a la ESP32 siempre llevan
        if mejor_c is None or (mejor_c[0] >= 2.0 and red not in con_etq):
            if red in con_etq:
                print('AVISO: sin lugar para la etiqueta de', red)
            continue
        _, x, y, dx, dy, caja = mejor_c
        etq_medias.append((red, x, y, dx, dy, tam))
        mapa.agrega(caja, 'etiqueta ' + red, True)

    def regla_general(i, cb, lados):
        bx0, bx1, by0, by1 = cb
        delgado = (bx1 - bx0) < 6 and (by1 - by0) > (bx1 - bx0)
        if i.ref.startswith('J') and len(lados) == 1:
            return 'abajo-izq' if (-1, 0) in lados else 'abajo-der' if (1, 0) in lados else 'abajo'
        if delgado and (1, 0) not in lados:
            return 'derecha'
        if (0, -1) not in lados and (0, 1) not in lados:
            return 'arriba-abajo'
        if (0, -1) not in lados:
            return 'arriba'
        if (bx1 - bx0) >= 8 and (by1 - by0) >= 8:
            return 'esquina'
        return 'derecha' if (1, 0) not in lados else 'izquierda'
    textos_pieza = {}
    for i in sorted(insts, key=lambda i: -len(i.ps)):
        if i.ref.startswith('#'):
            continue
        cb = caja_hoja(i, cuerpo(i.sym))
        lados = {pin_hoja(i, px, py, a)[2] for (_, num, _, px, py, a, _) in i.ps}
        ops = dict(TX.opciones_pieza(i.ref, i.p['value'], cb, lados))
        if TEXTO.get(i.ref):
            pos = ops[TEXTO[i.ref]]
        else:
            _c, _n, pos = TX.elegir(i.ref, i.p['value'], cb, lados, mapa,
                                    marco_de((cb[0] + cb[1]) / 2, (cb[2] + cb[3]) / 2), regla_general(i, cb, lados))
        a, b = TX.cajas_pieza(i.ref, i.p['value'], pos)
        mapa.agrega(a, 'ref ' + i.ref, True)
        mapa.agrega(b, 'valor ' + i.ref, True)
        textos_pieza[i.ref] = pos
    # revision: textos que todavia se enciman con algo
    encimados = set()
    for (caja, nombre, es_txt) in mapa.items:
        if not es_txt:
            continue
        for otro in mapa.choques(caja, ignora=(nombre,)):
            if nombre.startswith('etiqueta ') and otro == 'cable ' + nombre[9:]:
                continue
            encimados.add(tuple(sorted((nombre, otro))))
    print('textos encimados:', len(encimados))
    donde_esta = {n: c for (c, n, t) in mapa.items}
    for par in sorted(encimados)[:60]:
        c = donde_esta.get(par[0])
        print('  ENCIMADO: %s <-> %s   (x %.0f, y %.0f)' % (par[0], par[1], c[0], c[1]))

    # ---------- escribir la hoja
    libs = {}
    cuerpo_doc = []
    NS = uuid.uuid5(uuid.NAMESPACE_URL, 'openled/' + PROYECTO)
    fijo = lambda *k: str(uuid.uuid5(NS, '/'.join(str(x) for x in k)))   # mismos UUID en cada corrida: la PCB no se desenlaza
    root = fijo('raiz')
    for i in insts:
        libs[i.p['sym']] = i.sym
        su = fijo(i.ref, i.unidad)
        sx, sy = i.x, i.y
        bx0, bx1, by0, by1 = caja_hoja(i, cuerpo(i.sym))     # solo el cuerpo, sin pines
        lados = set()
        for (_, num, _, px, py, a, _) in i.ps:
            lados.add(pin_hoja(i, px, py, a)[2])
        cx, cy = GE.g((bx0 + bx1) / 2), GE.g((by0 + by1) / 2)
        delgado = (bx1 - bx0) < 6 and (by1 - by0) > (bx1 - bx0)
        ang = {0: 0, 90: 270, 180: 0, 270: 90}[i.rot % 360]     # el texto se ve horizontal y sin voltear en la hoja
        ref, val = i.ref, i.p['value']
        voltea = {'left': 'right', 'right': 'left'}

        def T(xr, yr, xv, yv, j=None):
            if j and (i.esp == 'y') != (i.rot % 360 == 180):      # con espejo o de cabeza KiCad voltea la justificacion
                j = voltea[j]
            return [GE.prop('Reference', ref, GE.g(xr), GE.g(yr), ang=ang, just=j), GE.prop('Value', val, GE.g(xv), GE.g(yv), ang=ang, just=j)]
        props = T(*textos_pieza.get(i.ref, (sx, sy, sx, sy, None)))
        oculto = i.ref.startswith('#')
        if oculto:
            props[0] = GE.prop('Reference', i.ref, sx, sy, True)
            if i.ref.startswith('#FLG'):   # el rombo basta; el texto PWR_FLAG solo estorba
                props[1] = GE.prop('Value', i.p['value'], sx, sy, True)
        props += [GE.prop('Footprint', i.p['fp'], sx, sy, True), GE.prop('Datasheet', '~', sx, sy, True)]
        espejo = [[S('mirror'), S(i.esp)]] if i.esp else []
        cuerpo_doc.append([S('symbol'), [S('lib_id'), i.p['sym']], [S('at'), sx, sy, i.rot]] + espejo + [[S('unit'), i.unidad],
                           [S('in_bom'), S('no') if oculto else S('yes')], [S('on_board'), S('no') if oculto else S('yes')],
                           [S('dnp'), S('yes') if i.p['dnp'] else S('no')], [S('uuid'), su]] + props +
                          [[S('pin'), num, [S('uuid'), fijo(i.ref, i.unidad, 'pin', num)]] for (_, num, *_r) in i.ps] +
                          [[S('instances'), [S('project'), PROYECTO, [S('path'), '/' + root, [S('reference'), i.ref], [S('unit'), i.unidad]]]]])
        i.p.setdefault('uuids_cab', {})[i.unidad] = su
        for (_, num, _, px, py, a, _) in i.ps:
            if i.p['pins'].get(num) is None:
                nx, ny, _d = pin_hoja(i, px, py, a)
                cuerpo_doc.append([S('no_connect'), [S('at'), GE.g(nx), GE.g(ny)], [S('uuid'), U()]])
    n_pot = 0
    for (x0, y0, x1, y1) in puentes_pot:
        cuerpo_doc.append([S('wire'), [S('pts'), [S('xy'), x0 * G, y0 * G], [S('xy'), x1 * G, y1 * G]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), U()]])
        cuerpo_doc.append([S('junction'), [S('at'), x0 * G, y0 * G], [S('diameter'), 0], [S('color'), 0, 0, 0, 0], [S('uuid'), U()]])
    for (ex, ey, fx, fy, rot, vx, vy, just, red) in pot_dibujo:
        libid, sym = simbolo_potencia(red)
        libs[libid] = sym
        cuerpo_doc.append([S('wire'), [S('pts'), [S('xy'), ex * G, ey * G], [S('xy'), fx * G, fy * G]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), U()]])
        if rot is None:
            continue
        n_pot += 1
        cuerpo_doc.append([S('symbol'), [S('lib_id'), libid], [S('at'), fx * G, fy * G, rot], [S('unit'), 1],
                           [S('in_bom'), S('no')], [S('on_board'), S('no')], [S('dnp'), S('no')], [S('uuid'), fijo('pwr', n_pot)],
                           GE.prop('Reference', '#PWR%04d' % n_pot, fx * G, fy * G, True),
                           GE.prop('Value', red, GE.g(vx), GE.g(vy), ang={0: 0, 90: 270, 180: 0, 270: 90}[rot], just=({'left': 'right', 'right': 'left'}.get(just) if rot == 180 else just)),
                           GE.prop('Footprint', '', fx * G, fy * G, True), GE.prop('Datasheet', '', fx * G, fy * G, True),
                           [S('pin'), '1', [S('uuid'), fijo('pwr', n_pot, 'pin')]],
                           [S('instances'), [S('project'), PROYECTO, [S('path'), '/' + root, [S('reference'), '#PWR%04d' % n_pot], [S('unit'), 1]]]]])
    for red, cam in segs:
        for (a, b) in a_segmentos(cam):
            cuerpo_doc.append([S('wire'), [S('pts'), [S('xy'), a[0] * G, a[1] * G], [S('xy'), b[0] * G, b[1] * G]],
                               [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), U()]])

    def etiqueta(red, x, y, dx, dy, tam):
        ang, just = {(1, 0): (0, 'left'), (-1, 0): (180, 'right'), (0, -1): (90, 'left'), (0, 1): (270, 'right')}[(dx, dy)]
        cuerpo_doc.append([S('label'), red, [S('at'), x * G, y * G, ang], [S('fields_autoplaced')],
                           [S('effects'), [S('font'), [S('size'), tam, tam]], [S('justify'), S(just), S('bottom')]], [S('uuid'), U()]])
    # etiquetas de las redes que van a la ESP32: tramo corto desde el pin y la etiqueta en su punta
    for (ex, ey, fx, fy, dx, dy, red) in tramos_etq:
        cuerpo_doc.append([S('wire'), [S('pts'), [S('xy'), ex * G, ey * G], [S('xy'), fx * G, fy * G]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), U()]])
        etiqueta(red, fx, fy, dx, dy, 1.27)
    for (tx, ty, ex, ey) in tramos_puerto:
        cuerpo_doc.append([S('wire'), [S('pts'), [S('xy'), tx * G, ty * G], [S('xy'), ex * G, ey * G]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), U()]])
    for (ex, ey, dx, dy, red) in puertos:
        etiqueta(red, ex, ey, dx, dy, 1.27)
    for (red, x, y, dx, dy, tam) in etq_medias:     # nombre de cada red cableada, donde no choca
        etiqueta(red, x, y, dx, dy, tam)
    # uniones: celdas con 3 o mas conexiones de la misma red (contando el pin)
    grado = {}
    for (a, b), n in rej.aristas.items():
        grado[(a, n)] = grado.get((a, n), 0) + 1
        grado[(b, n)] = grado.get((b, n), 0) + 1
    pines = {(rej.i(x, y), ids[r]) for r, ps in redes_pines.items() for (x, y, d) in ps}
    for (c, n), k in grado.items():
        if k + (1 if (c, n) in pines else 0) >= 3:
            cuerpo_doc.append([S('junction'), [S('at'), (c % W) * G, (c // W) * G], [S('diameter'), 0], [S('color'), 0, 0, 0, 0], [S('uuid'), U()]])
    # conexiones que no se pudieron trazar: etiqueta en ambos lados (para no perder la conexion)
    for red, (x, y) in fallidas:
        cuerpo_doc.append([S('global_label'), red, [S('shape'), S('passive')], [S('at'), x * G, y * G, 0], [S('fields_autoplaced')],
                           [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], [S('justify'), S('left')]], [S('uuid'), U()],
                           [S('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [S('at'), x * G, y * G, 0], [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], S('hide')]]])
    redes_fallidas = {r for r, _ in fallidas}
    for red in redes_fallidas:   # el resto de los pines de esa red tambien llevan su etiqueta
        x, y, d = redes_pines[red][0]
        cuerpo_doc.append([S('global_label'), red, [S('shape'), S('passive')], [S('at'), x * G, y * G, 0], [S('fields_autoplaced')],
                           [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], [S('justify'), S('left')]], [S('uuid'), U()],
                           [S('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [S('at'), x * G, y * G, 0], [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], S('hide')]]])
    for t in titulos:
        if t[0] == 'marco':      # bloque con marco punteado y su titulo adentro, arriba a la izquierda
            _, titulo, x0, y0, x1, y1 = t
            cuerpo_doc.append([S('rectangle'), [S('start'), x0, y0], [S('end'), x1, y1],
                               [S('stroke'), [S('width'), 0.3], [S('type'), S('dash')], [S('color'), 0, 0, 132, 1]],
                               [S('fill'), [S('type'), S('none')]], [S('uuid'), U()]])
            cuerpo_doc.append([S('text'), titulo.upper(), [S('at'), x0 + 2.54, y0 + 4.45, 0],
                               [S('effects'), [S('font'), [S('size'), 2.0, 2.0], [S('thickness'), 0.4], S('bold'), [S('color'), 0, 0, 132, 1]],
                                [S('justify'), S('left')]], [S('uuid'), U()]])
            continue
        titulo, bx, by = t
        cuerpo_doc.append([S('text'), titulo.upper(), [S('at'), bx, by + 5.08, 0],
                           [S('effects'), [S('font'), [S('size'), 4, 4], [S('thickness'), 0.8], S('bold')], [S('justify'), S('left')]], [S('uuid'), U()]])
    comentarios = getattr(diseno, 'COMENTARIOS', ['Hoja unica con cables; alimentacion con simbolos. Generado por generador/gen_esquematico_cableado.py'])
    doc = [S('kicad_sch'), [S('version'), 20230121], [S('generator'), S('eeschema')], [S('uuid'), root], [S('paper'), PAPEL],
           [S('title_block'), [S('title'), getattr(diseno, 'TITULO', 'Tarjeta OpenLed S3')], [S('date'), GE.FECHA],
            [S('rev'), getattr(diseno, 'REVISION', 'B')], [S('company'), 'OpenLed']] +
           [[S('comment'), k + 1, c] for k, c in enumerate(comentarios)],
           [S('lib_symbols')] + list(libs.values())] + cuerpo_doc + [[S('sheet_instances'), [S('path'), '/', [S('page'), '1']]]]
    # libreria: agregar los simbolos de alimentacion propios
    lib = os.path.join(SALIDA, 'openled.kicad_sym')
    from sexpr import parse
    L = parse(open(lib).read())[0]
    for libid, sym in libs.items():
        if libid.startswith('openled:PWR_'):
            s2 = copy.deepcopy(sym); s2[1] = libid.split(':')[1]
            L.append(s2)
    open(lib, 'w').write(dump(L) + '\n')
    for f in os.listdir(SALIDA):   # quitar las hojas del esquematico jerarquico
        if f.endswith('.kicad_sch'):
            os.remove(os.path.join(SALIDA, f))
    open(os.path.join(SALIDA, PROYECTO + '.kicad_sch'), 'w').write(dump(doc) + '\n')
    return root, insts, segs, fallidas

if __name__ == '__main__':
    root, insts, segs, fallidas = generar()
    print('simbolos', len(insts), 'redes cableadas', len({r for r, _ in segs}), 'conexiones sin trazar', len(fallidas))
    for r, t in fallidas[:20]:
        print('  sin trazar:', r)
