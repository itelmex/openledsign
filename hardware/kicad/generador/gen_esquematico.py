"""Genera la libreria propia y el esquematico (KiCad 7, una hoja por bloque) a partir de diseno.py."""
import os, uuid, datetime
from sexpr import Sym, dump, find, find1
import libsym
import diseno

PROYECTO = 'tarjeta_openled_s3'
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FILA_DEVKIT_MM = 25.40   # distancia entre las dos filas de pines de la DevKit: MEDIRLA antes de fabricar
FILA_DEVKIT_ANGOSTA_MM = 22.86   # DevKitC-1 oficial de Espressif (DXF v1.1): 3.a fila en paralelo con la del lado GND/TX/RX
FECHA = datetime.date.today().isoformat()

def U():
    return str(uuid.uuid4())

S = Sym

# ============================================================
#  LIBRERIA PROPIA: simbolo y huella de la DevKit
# ============================================================
IZQ = ["3V3", "3V3", "RST", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO8",
       "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "5V", "GND"]
DER = ["GND", "TX/GPIO43", "RX/GPIO44", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38", "GPIO37",
       "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19", "GND", "GND"]

def fuente(size=1.27):
    return [S('effects'), [S('font'), [S('size'), size, size]]]

def prop(nombre, valor, x, y, oculto=False, ang=0, just=None):
    ef = fuente()
    if just:
        ef.append([S('justify')] + [S(j) for j in just.split()])
    if oculto:
        ef.append(S('hide'))
    return [S('property'), nombre, valor, [S('at'), x, y, ang], ef]

def simbolo_devkit():
    pines = []
    for i, nm in enumerate(IZQ):
        pines.append([S('pin'), S('passive'), S('line'), [S('at'), -17.78, 26.67 - 2.54 * i, 0], [S('length'), 5.08],
                      [S('name'), nm, fuente()], [S('number'), str(i + 1), fuente()]])
    for i, nm in enumerate(DER):
        pines.append([S('pin'), S('passive'), S('line'), [S('at'), 17.78, 26.67 - 2.54 * i, 180], [S('length'), 5.08],
                      [S('name'), nm, fuente()], [S('number'), str(23 + i), fuente()]])
    cuerpo = [S('symbol'), 'ESP32-S3-DevKitC-1_0_1',
              [S('rectangle'), [S('start'), -12.7, 29.21], [S('end'), 12.7, -29.21],
               [S('stroke'), [S('width'), 0.254], [S('type'), S('default')]], [S('fill'), [S('type'), S('background')]]]]
    return [S('symbol'), 'ESP32-S3-DevKitC-1', [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
            prop('Reference', 'U', 0, 31.75), prop('Value', 'ESP32-S3-DevKitC-1', 0, -31.75),
            prop('Footprint', 'openled:ESP32-S3-DevKitC-1_Zocalo', 0, -34.29, True),
            prop('Datasheet', 'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/', 0, -36.83, True),
            prop('ki_description', 'ESP32-S3-DevKitC-1 (clon N16R8, 2025-V1.4) en zocalo de 2x22', 0, 0, True),
            cuerpo, [S('symbol'), 'ESP32-S3-DevKitC-1_1_1'] + pines]

def escribir_libreria():
    lib = [S('kicad_symbol_lib'), [S('version'), 20220914], [S('generator'), S('openled_gen')], simbolo_devkit()]
    open(os.path.join(SALIDA, 'openled.kicad_sym'), 'w').write(dump(lib) + '\n')
    os.makedirs(os.path.join(SALIDA, 'openled.pretty'), exist_ok=True)
    w = FILA_DEVKIT_MM
    largo = 21 * 2.54
    pads = []
    # tercera fila (pads 23-44 repetidos) a FILA_DEVKIT_ANGOSTA_MM para la DevKitC-1 oficial de Espressif, mas angosta;
    # mismo orden de pines que el clon ancho. Las filas de 25.40 y 22.86 van en una tira hembra de 2x22.
    for fila, x in ((0, 0.0), (1, w), (1, FILA_DEVKIT_ANGOSTA_MM)):
        for i in range(22):
            n = fila * 22 + i + 1
            forma = 'rect' if n == 1 else 'oval'
            pads.append('  (pad "%d" thru_hole %s (at %.3f %.3f) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))' % (n, forma, x, i * 2.54))
    m = 3.0
    usb = 3.0   # la oficial sale 6.1 mm mas que el clon por el lado del USB (8.00 mm del pin 22 a su orilla)
    txt = '''(footprint "ESP32-S3-DevKitC-1_Zocalo" (version 20221018) (generator openled_gen)
  (layer "F.Cu")
  (descr "Zocalo para ESP32-S3-DevKitC-1: clon ancho N16R8 (filas a %.2f mm) u oficial angosta (filas a %.2f mm). Tira hembra 1x22 + 2x22. MEDIR la DevKit antes de fabricar.")
  (attr through_hole)
  (fp_text reference "REF**" (at %.3f -9) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text value "ESP32-S3-DevKitC-1_Zocalo" (at %.3f %.3f) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text user "ANTENA: sin cobre debajo" (at %.3f -4.5) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
  (fp_text user "USB" (at %.3f %.3f) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start %.3f -7) (end %.3f %.3f) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))
  (fp_rect (start %.3f -7.25) (end %.3f %.3f) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
  (fp_line (start %.3f -1.5) (end %.3f -1.5) (stroke (width 0.12) (type dash)) (layer "F.SilkS"))
%s
)
''' % (w, FILA_DEVKIT_ANGOSTA_MM, w / 2, w / 2, largo + 6 + usb, w / 2, w / 2, largo + 3.5, -m + 1.5, w + m - 1.5, largo + 5 + usb, -m + 1.25, w + m - 1.25, largo + 5.25 + usb,
       -m + 1.5, w + m - 1.5, '\n'.join(pads))
    open(os.path.join(SALIDA, 'openled.pretty', 'ESP32-S3-DevKitC-1_Zocalo.kicad_mod'), 'w').write(txt)
    modulo_w5500()
    modulo_yl97()


from comun import W5500, w5500_barrenos, w5500_x0   # medidas y barrenos del modulo


def modulo_yl97():
    """Modulo RS232 YL-97 (MAX3232, DB9 macho, 30 x 26 x 15 mm) enchufado en tira hembra 1x4. La tira va en la orilla
    trasera del modulo; el DB9 sobresale de la orilla de la tarjeta (la huella solo aparta la parte que queda encima).
    Posicion de la tira y barrenos POR CONFIRMAR con el modulo real."""
    pads = ['  (pad "%d" thru_hole %s (at %.3f 0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))'
            % (n + 1, 'rect' if n == 0 else 'oval', -3.81 + 2.54 * n) for n in range(4)]
    txt = """(footprint "Modulo_YL97" (version 20221018) (generator openled_gen)
  (layer "F.Cu")
  (descr "Modulo RS232 YL-97 (MAX3232, DB9 macho) en tira hembra 1x4: 1 TXD, 2 RXD, 3 VCC, 4 GND (como su serigrafia). El DB9 sobresale de la orilla. POR CONFIRMAR con el modulo real.")
  (attr through_hole)
  (fp_text reference "REF**" (at 0 -3.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text value "Modulo_YL97" (at 0 10) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text user "YL-97: DB9 hacia afuera" (at 0 14) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text user "TXD RXD VCC GND" (at 0 2.6) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
  (fp_rect (start -15 -2) (end 15 18) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))
  (fp_rect (start -15.25 -2.25) (end 15.25 18) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
%s
)
""" % '\n'.join(pads)
    open(os.path.join(SALIDA, 'openled.pretty', 'Modulo_YL97.kicad_mod'), 'w').write(txt)


def modulo_w5500():
    L, A, m = W5500['largo'], W5500['ancho'], W5500['margen_tira']
    pads = []
    # numeros = los del modulo azul comun (serigrafia): 1 NC, 2 INT, 3 RST, 4 GND, 5 5V en la columna de la
    # orilla; 6 SCLK, 7 SCS, 8 MOSI, 9 MISO, 10 3.3V en la de adentro. Visto desde arriba con el RJ45 abajo,
    # el pin 1 queda a la derecha. Los clones pueden cambiar la orientacion: revisar contra el modulo real.
    for i in range(5):
        for fila in (0, 1):
            n = 5 - i + 5 * fila
            pads.append('  (pad "%d" thru_hole %s (at %.3f %.3f) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))'
                        % (n, 'rect' if n == 1 else 'oval', i * 2.54, fila * 2.54))
    x0, x1 = w5500_x0(), w5500_x0() + A      # la fila del 5V va junto a una orilla larga
    y0, y1 = -m, L - m                       # el RJ45 queda en y1
    txt = '''(footprint "Modulo_W5500" (version 20221018) (generator openled_gen)
  (layer "F.Cu")
  (descr "Modulo Ethernet W5500 azul comun en tira hembra 2x5 (2.54 mm), pines numerados como su serigrafia. Contorno de %.0f x %.0f mm POR CONFIRMAR con el modulo real.")
  (attr through_hole)
  (fp_text reference "REF**" (at 5.08 -%.3f) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text value "Modulo_W5500" (at 5.08 %.3f) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text user "RJ45" (at 5.08 %.3f) (layer "F.SilkS") (effects (font (size 1.2 1.2) (thickness 0.15))))
  (fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))
  (fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
%s
%s
)
''' % (L, A, m + 1.2, L / 2, y1 - 4, x0, y0, x1, y1, x0 - 0.25, y0 - 0.25, x1 + 0.25, y1 + 0.25, '\n'.join(pads),
       '\n'.join('  (fp_circle (center %.3f %.3f) (end %.3f %.3f) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))'
                 % (x, y, x + 3.0, y) for x, y in w5500_barrenos()))
    open(os.path.join(SALIDA, 'openled.pretty', 'Modulo_W5500.kicad_mod'), 'w').write(txt)
    open(os.path.join(SALIDA, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n  (lib (name "openled")(type "KiCad")(uri "${KIPRJMOD}/openled.kicad_sym")(options "")(descr "OpenLed"))\n)\n')
    open(os.path.join(SALIDA, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n  (lib (name "openled")(type "KiCad")(uri "${KIPRJMOD}/openled.pretty")(options "")(descr "OpenLed"))\n)\n')

# ============================================================
#  ESQUEMATICO
# ============================================================
def cargar_simbolo(libid):
    if libid.startswith('openled:'):
        return libsym.get(libid, os.path.join(SALIDA, 'openled.kicad_sym'))
    return libsym.get(libid)

def caja(sym):
    xs, ys = [], []
    def rec(e):
        if isinstance(e, list) and e:
            if e[0] in ('xy', 'start', 'end') and len(e) >= 3:
                xs.append(float(e[1])); ys.append(float(e[2]))
            elif e[0] == 'pin':
                at = find1(e, 'at')
                xs.append(float(at[1])); ys.append(float(at[2]))
            elif e[0] == 'circle':
                c = find1(e, 'center'); r = float(find1(e, 'radius')[1])
                xs.extend([float(c[1]) - r, float(c[1]) + r]); ys.extend([float(c[2]) - r, float(c[2]) + r])
            for x in e[1:]:
                rec(x)
    for u in find(sym, 'symbol'):
        rec(u)
    return min(xs), max(xs), min(ys), max(ys)

DIR = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # hacia afuera del simbolo, coordenadas de la hoja (Y abajo)
ANG_ETIQ = {0: 180, 180: 0, 90: 270, 270: 90}

def g(v):
    return round(round(v / 1.27) * 1.27, 4)

def largo_etiqueta(red):
    return len(red) * 1.05 + 4

PAPEL = [('A4', 297, 210), ('A3', 420, 297), ('A2', 594, 420), ('A1', 841, 594), ('A0', 1189, 841)]

def instancias(hoja):
    """[(parte, unidad, simbolo, pines_de_la_unidad)]"""
    out = []
    for p in diseno.partes:
        if p['hoja'] != hoja:
            continue
        sym = cargar_simbolo(p['sym'])
        allp = libsym.pins(sym)
        for un in (p['unidades'] or [1]):
            ps = [x for x in allp if x[0] in (0, un)]
            out.append((p, un, sym, ps))
    return out

def angosto(sym):
    x0, x1, y0, y1 = caja(sym)
    return (x1 - x0) < 6 and (y1 - y0) > (x1 - x0)

texto_lateral = 0

def medidas(sym, ps, conex):
    x0, x1, y0, y1 = caja(sym)
    izq = der = arr = aba = 0.0
    for (_, num, _, x, y, a, _) in ps:
        red = conex.get(num)
        l = 2.54 + (largo_etiqueta(red) if red else 1.5)
        if a == 0: izq = max(izq, l)
        elif a == 180: der = max(der, l)
        elif a == 90: aba = max(aba, l)
        else: arr = max(arr, l)
    # caja en la hoja (Y abajo): lib y -> -y
    if angosto(sym):   # referencia y valor van a la derecha del simbolo
        return (x0 - izq, x1 + max(der, 2.54 + 1.1 * texto_lateral), -y1 - arr - 1.5, -y0 + aba + 1.5)
    return (x0 - izq, x1 + der, -y1 - arr - 3.5, -y0 + aba + 3.5)

def generar_hoja(nombre, titulo, root_uuid, hoja_uuid, pagina):
    items = instancias(nombre)
    libs = {}
    cajas = []
    for (p, un, sym, ps) in items:
        libs[p['sym']] = sym
        global texto_lateral
        texto_lateral = max(len(p['ref']), len(p['value']))
        cajas.append(medidas(sym, ps, p['pins']))
    # empaque por renglones; se prueba con hojas cada vez mas grandes
    for papel, W, H in PAPEL:
        x, y, alto_fila = 25.4, 30.48, 0.0
        pos = []
        ok = True
        for (cx0, cx1, cy0, cy1) in cajas:
            w, hgt = cx1 - cx0 + 5, cy1 - cy0 + 3
            if x + w > W - 20:
                x = 25.4; y += alto_fila; alto_fila = 0
            pos.append((g(x - cx0), g(y - cy0)))
            x += w
            alto_fila = max(alto_fila, hgt)
        if y + alto_fila < H - 35:
            break
    cuerpo = []
    for (p, un, sym, ps), (sx, sy) in zip(items, pos):
        x0, x1, y0, y1 = caja(sym)
        su = U()
        if angosto(sym):
            props = [prop('Reference', p['ref'], g(sx + x1 + 1.27), g(sy - 1.27), just='left'),
                     prop('Value', p['value'], g(sx + x1 + 1.27), g(sy + 1.27), just='left')]
        else:
            props = [prop('Reference', p['ref'], sx, g(sy - y1 - 2.54)), prop('Value', p['value'], sx, g(sy - y0 + 2.54))]
        props += [prop('Footprint', p['fp'], sx, sy, True), prop('Datasheet', '~', sx, sy, True)]
        if p['nota']:
            props.append(prop('Nota', p['nota'], sx, sy, True))
        pins_uuid = [[S('pin'), num, [S('uuid'), U()]] for (_, num, _, _, _, _, _) in ps]
        cuerpo.append([S('symbol'), [S('lib_id'), p['sym']], [S('at'), sx, sy, 0], [S('unit'), un],
                       [S('in_bom'), S('no') if p['ref'].startswith('#') else S('yes')], [S('on_board'), S('no') if p['ref'].startswith('#') else S('yes')],
                       [S('dnp'), S('yes') if p['dnp'] else S('no')], [S('uuid'), su]] + props + pins_uuid +
                      [[S('instances'), [S('project'), PROYECTO, [S('path'), '/%s/%s' % (root_uuid, hoja_uuid), [S('reference'), p['ref']], [S('unit'), un]]]]])
        p.setdefault('uuids', {})[un] = su
        p['hoja_uuid'] = hoja_uuid
        for (_, num, _, px, py, a, _) in ps:
            ex, ey = g(sx + px), g(sy - py)
            red = p['pins'].get(num)
            if red is None:
                cuerpo.append([S('no_connect'), [S('at'), ex, ey], [S('uuid'), U()]])
                continue
            dx, dy = DIR.get(a, (-1, 0))
            lx, ly = g(ex + dx * 2.54), g(ey + dy * 2.54)
            cuerpo.append([S('wire'), [S('pts'), [S('xy'), ex, ey], [S('xy'), lx, ly]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), U()]])
            ang = ANG_ETIQ.get(a, 180)
            just = 'left' if ang in (0, 90) else 'right'
            cuerpo.append([S('global_label'), red, [S('shape'), S('passive')], [S('at'), lx, ly, ang], [S('fields_autoplaced')],
                           [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], [S('justify'), S(just)]], [S('uuid'), U()],
                           [S('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [S('at'), lx, ly, 0],
                            [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], S('hide')]]])
    cuerpo.append([S('text'), titulo.upper(), [S('at'), 25.4, 20.32, 0],
                   [S('effects'), [S('font'), [S('size'), 3, 3], [S('thickness'), 0.6], S('bold')], [S('justify'), S('left')]], [S('uuid'), U()]])
    doc = [S('kicad_sch'), [S('version'), 20230121], [S('generator'), S('eeschema')], [S('uuid'), hoja_uuid if False else U()],
           [S('paper'), papel],
           [S('title_block'), [S('title'), 'Tarjeta OpenLed S3 - ' + titulo], [S('date'), FECHA], [S('rev'), 'B'],
            [S('company'), 'OpenLed'], [S('comment'), 1, 'Generado por generador/gen_esquematico.py - primera version para revisar']],
           [S('lib_symbols')] + list(libs.values())] + cuerpo
    archivo = nombre + '.kicad_sch'
    open(os.path.join(SALIDA, archivo), 'w').write(dump(doc) + '\n')
    return archivo, papel

def generar():
    escribir_libreria()
    root_uuid = U()
    hojas = []
    for i, (nombre, titulo) in enumerate(diseno.HOJAS):
        hu = U()
        archivo, papel = generar_hoja(nombre, titulo, root_uuid, hu, i + 2)
        hojas.append((nombre, titulo, archivo, hu, papel))
    cuerpo = []
    for i, (nombre, titulo, archivo, hu, papel) in enumerate(hojas):
        x, y = 30.48 + (i % 3) * 88.9, 50.8 + (i // 3) * 50.8
        cuerpo.append([S('sheet'), [S('at'), x, y], [S('size'), 63.5, 25.4], [S('fields_autoplaced')],
                       [S('stroke'), [S('width'), 0.1524], [S('type'), S('solid')]], [S('fill'), [S('color'), 0, 0, 0, 0.0]],
                       [S('uuid'), hu],
                       [S('property'), 'Sheetname', titulo, [S('at'), x, y - 0.7, 0], [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], [S('justify'), S('left'), S('bottom')]]],
                       [S('property'), 'Sheetfile', archivo, [S('at'), x, y + 26.0, 0], [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], [S('justify'), S('left'), S('top')]]],
                       [S('instances'), [S('project'), PROYECTO, [S('path'), '/' + root_uuid, [S('page'), str(i + 2)]]]]])
    notas = ('Tarjeta OpenLed S3 Rev B - primera version generada automaticamente desde generador/diseno.py.\n'
             'Las conexiones entre hojas son etiquetas globales con el nombre de la red.\n'
             'Antes de fabricar: medir la distancia entre filas de la DevKit (FILA_DEVKIT_MM), verificar el orden de pines\n'
             'del modulo W5500 que se compre, revisar huellas de borneras, reles y conectores contra las piezas reales.')
    cuerpo.append([S('text'), notas, [S('at'), 30.48, 165.1, 0], [S('effects'), [S('font'), [S('size'), 2, 2]], [S('justify'), S('left'), S('top')]], [S('uuid'), U()]])
    doc = [S('kicad_sch'), [S('version'), 20230121], [S('generator'), S('eeschema')], [S('uuid'), root_uuid], [S('paper'), 'A3'],
           [S('title_block'), [S('title'), 'Tarjeta OpenLed S3'], [S('date'), FECHA], [S('rev'), 'B'], [S('company'), 'OpenLed']],
           [S('lib_symbols')]] + cuerpo + [[S('sheet_instances'), [S('path'), '/', [S('page'), '1']]]]
    open(os.path.join(SALIDA, PROYECTO + '.kicad_sch'), 'w').write(dump(doc) + '\n')
    return root_uuid, hojas

if __name__ == '__main__':
    r, hojas = generar()
    for h in hojas:
        print(h[2], h[4])
    print('piezas:', len([p for p in diseno.partes if not p['ref'].startswith('#')]))
