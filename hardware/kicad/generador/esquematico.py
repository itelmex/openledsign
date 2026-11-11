"""Genera el esquematico de OpenLed (hoja unica con cables), lo revisa contra el diseno y exporta PDF.

    python3 esquematico.py            # con la plantilla a mano (plantilla_openled.py)
    python3 esquematico.py --auto     # acomodo automatico por bloques (solo para arrancar una plantilla)

Salida en ../ (openled.kicad_sch, openled.kicad_pro, openled.pdf, librerias openled.*).
Revision: exporta la netlist con kicad-cli de KiCad 10 (flatpak; el kicad-cli 7 del sistema no conecta bien algunos
pines) y compara pin por pin contra diseno_openled.py.
"""
import os, sys, subprocess, json

BASE = os.path.dirname(os.path.abspath(__file__))
KICAD_CLI = ['flatpak', 'run', '--command=kicad-cli', 'org.kicad.KiCad']
sys.path.insert(0, BASE)
import diseno_openled as mod
sys.modules['diseno'] = mod
if '--auto' in sys.argv:
    mod.PLANTILLA = None
import gen_esquematico as GE
GE.SALIDA = os.path.abspath(os.path.join(BASE, '..'))
GE.PROYECTO = 'openled'
import gen_esquematico_cableado as GC
GC.SALIDA, GC.PROYECTO = GE.SALIDA, GE.PROYECTO

root, insts, segs, fallidas = GC.generar()
print('simbolos', len(insts), '| redes cableadas', len({r for r, _ in segs}), '| conexiones sin trazar', len(fallidas))
for r, t in fallidas:
    print('  SIN TRAZAR:', r)

sch = os.path.join(GE.SALIDA, 'openled.kicad_sch')
pro = os.path.join(GE.SALIDA, 'openled.kicad_pro')
if not os.path.exists(pro):
    json.dump({"meta": {"filename": "openled.kicad_pro", "version": 1}, "schematic": {}, "sheets": [],
               "text_variables": {}}, open(pro, 'w'), indent=2)

# ---- revision: misma conexion que el diseno (por grupos de pines)
from sexpr import parse, find, find1
net = os.path.join(GE.SALIDA, 'netlist_tmp.net')   # dentro del proyecto: flatpak no escribe en /tmp
subprocess.run(KICAD_CLI + ['sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net, sch], check=True,
               capture_output=True)
N = parse(open(net).read())[0]
os.remove(net)
red_de_pin = {}
for n in find(find1(N, 'nets'), 'net'):
    nombre = find1(n, 'name')[1]
    for nd in find(n, 'node'):
        red_de_pin[(find1(nd, 'ref')[1], find1(nd, 'pin')[1])] = nombre
grupos = {}
for p in mod.partes:
    if p['ref'].startswith('#'):
        continue
    for pin, r in p['pins'].items():
        grupos.setdefault(r, set()).add((p['ref'], pin))
errores = 0
for r, pines in sorted(grupos.items()):
    nombres = {red_de_pin.get(x) for x in pines}
    if len(nombres) != 1 or None in nombres:
        errores += 1; print('  CONEXION DISTINTA:', r, sorted(nombres, key=str)); continue
    nk = nombres.pop()
    otros = {x for x, n2 in red_de_pin.items() if n2 == nk and not x[0].startswith('#')}
    if otros != pines:
        errores += 1; print('  CONEXION DISTINTA:', r, 'sobran', sorted(otros - pines))
print('revision contra el diseno: %d errores en %d redes' % (errores, len(grupos)))

# ---- ERC y PDF
erc = os.path.join(GE.SALIDA, 'erc.rpt')
r = subprocess.run(KICAD_CLI + ['sch', 'erc', '-o', erc, sch], capture_output=True)
for l in (open(erc).read().splitlines() if os.path.exists(erc) else ['ERC: esta version de kicad-cli no lo tiene']):
    if 'violations' in l.lower() or l.startswith('ERC'):
        print(' ', l)
subprocess.run(KICAD_CLI + ['sch', 'export', 'pdf', '-o', os.path.join(GE.SALIDA, 'openled_esquematico.pdf'), sch],
               check=True, capture_output=True)
print('PDF:', os.path.join(GE.SALIDA, 'openled_esquematico.pdf'))
