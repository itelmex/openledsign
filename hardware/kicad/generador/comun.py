"""Ayudas compartidas por las listas de piezas de la version inicial (todo de agujero pasante)."""
from collections import defaultdict

FP = {
    'R': 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal',       # 1/4 W (paso corto: ahorra lugar)
    'R2': 'Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal',      # 1/2 W
    'C': 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    'CP5': 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm',
    'CP6': 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
    'LED': 'LED_THT:LED_D3.0mm',
    'TO92': 'Package_TO_SOT_THT:TO-92_Inline',
    'D35': 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal',
    'D41': 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal',
    'D15': 'Diode_THT:D_DO-15_P12.70mm_Horizontal',
    'PTC': 'Fuse:Fuse_Bourns_MF-RHT050',
    'TB': 'Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_{n}-G-5,08_1x{n:02d}_P5.08mm_Horizontal',
    'TB35': 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_{n}-G-3.5_1x{n:02d}_P3.50mm_Horizontal',
    'HDR': 'Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical',
    'HDR2': 'Connector_PinHeader_2.54mm:PinHeader_2x{n:02d}_P2.54mm_Vertical',
    'IDC': 'Connector_IDC:IDC-Header_2x{n:02d}_P2.54mm_Vertical',
    'JMP3': 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    'JMP2': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    'TP': 'TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm',
    'HOLE': 'MountingHole:MountingHole_3.2mm_M3_Pad_Via',
}

# Conectores entre tarjetas (cable plano IDC). La controladora reparte la alimentacion.
IDC_ENTRADAS = {1: '+3V3', 2: 'GND', 3: 'SDA', 4: 'SCL', 5: 'LAZO_C1A', 6: 'GND', 7: 'LAZO_C1B', 8: 'LAZO_C2A',
                9: 'LAZO_C2B', 10: 'FOTO1', 11: 'FOTO2', 12: 'GND', 13: '+VSENS', 14: '+VSENS'}
IDC_BARRERAS = {1: '+5V', 2: '+5V', 3: 'GND', 4: 'GND', 5: '+3V3', 6: 'SDA', 7: 'SCL', 8: 'GND', 9: '+VSENS', 10: '+VSENS'}
IDC_ANALOGICAS = {1: '+3V3', 2: 'GND', 3: 'SDA', 4: 'SCL', 5: 'GND', 6: '+VIN', 7: '+VIN', 8: 'GND'}


# Modulo W5500 comun (placa azul HW-243 con RJ45 HR911105A): tira 2x5 en un extremo y el RJ45 en el otro.
# Medidas del modelo 3D de 3D Warehouse (W5500 Ethernet Network Module, con fotos del modulo como textura);
# confirmar con vernier en el modulo real.
W5500 = dict(largo=55.0, ancho=27.0,
             margen_tira=2.3,    # de la columna de los pines 1-5 a la orilla corta de la tira
             orilla_5v=1.7,      # de la fila 5V / 3.3V (pines 5 y 10) a su orilla larga: la tira NO va centrada
             # barrenos del modulo (3.0 mm, para postes): (a, b) en mm, centro del barreno medido desde la orilla de
             # la tira (a) y desde la orilla larga del lado del pin 5V (b). Los dos van en la orilla del RJ45.
             barrenos=[(52.5, 2.5), (52.5, 24.5)])


def w5500_x0():
    """Orilla larga del lado del 5V en coordenadas de la huella (pad 5 en 0,0; los pads crecen hacia +x)."""
    return -W5500['orilla_5v']


def w5500_barrenos():
    """Centros de los barrenos del modulo en coordenadas de su huella (pad 5 en 0,0)."""
    x0 = w5500_x0()
    return [(x0 + b, a - W5500['margen_tira']) for a, b in W5500['barrenos']]


class Lista:
    def __init__(self):
        self.partes = []
        self.cuenta = defaultdict(int)

    def P(self, prefijo, simbolo, valor, huella, pines, hoja, unidades=None, dnp=False, nota='', cerca=None):
        self.cuenta[prefijo] += 1
        ref = '%s%d' % (prefijo, self.cuenta[prefijo])
        self.partes.append(dict(ref=ref, sym=simbolo, value=valor, fp=huella, pins={str(k): v for k, v in pines.items() if v},
                                hoja=hoja, unidades=unidades, dnp=dnp, nota=nota, cerca=cerca))
        return ref

    def R(self, valor, a, b, hoja, fp=FP['R']):
        return self.P('R', 'Device:R', valor, fp, {1: a, 2: b}, hoja)

    def C(self, valor, a, b, hoja, fp=FP['C'], cerca=None):
        """cerca: referencia del chip que desacopla (va junto a sus pines de alimentacion)."""
        return self.P('C', 'Device:C', valor, fp, {1: a, 2: b}, hoja, cerca=cerca)

    def CP(self, valor, pos, neg, hoja, fp=FP['CP5']):
        return self.P('C', 'Device:C_Polarized', valor, fp, {1: pos, 2: neg}, hoja)

    def D(self, valor, k, a, hoja, fp=FP['D35'], sym='Device:D'):
        return self.P('D', sym, valor, fp, {1: k, 2: a}, hoja)

    def clamp(self, senal, hoja):
        """Dos diodos Schottky axiales: limitan la senal entre GND y +3V3."""
        self.D('BAT85', senal, 'GND', hoja, sym='Device:D_Schottky')
        self.D('BAT85', '+3V3', senal, hoja, sym='Device:D_Schottky')

    def borne(self, nombre_pines, hoja, valor, paso=3.5):
        n = len(nombre_pines)
        return self.P('J', 'Connector:Screw_Terminal_01x%02d' % n, valor, FP['TB35' if paso == 3.5 else 'TB'].format(n=n),
                      {i + 1: r for i, r in enumerate(nombre_pines)}, hoja)

    def idc(self, pines, hoja, valor):
        n = max(pines) // 2 + (max(pines) % 2)
        n = 7 if max(pines) > 10 else 5
        return self.P('J', 'Connector_Generic:Conn_02x%02d_Odd_Even' % n, valor, FP['IDC'].format(n=n), pines, hoja)

    def flag(self, red, hoja):
        return self.P('#FLG0', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: red}, hoja)

    def postes(self, hoja, modulo, n):
        """Barrenos M3 para los postes de un modulo enchufable; el generador los pone donde caen los del modulo."""
        for _ in range(n):
            self.P('H', 'Mechanical:MountingHole_Pad', 'Poste ' + modulo, FP['HOLE'], {1: 'GND'}, hoja, cerca=modulo)

    def agujeros(self, hoja, n=4):
        for _ in range(n):
            self.P('H', 'Mechanical:MountingHole_Pad', 'M3', FP['HOLE'], {1: 'GND'}, hoja)
