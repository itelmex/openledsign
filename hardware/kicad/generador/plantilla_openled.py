"""Acomodo a mano del esquematico de OpenLed Rev A (hoja A2, 594 x 420 mm).

Cada pieza: ref -> (x, y, rotacion, espejo), en mm de la hoja (Y hacia abajo); el generador ajusta a 1.27 mm.
Rotacion en grados contra reloj (como KiCad); espejo None, 'x' (arriba-abajo) o 'y' (izquierda-derecha).

    fila 1:  Alimentacion | ESP32-S3 | Entradas, reles y expansor | RS485
    fila 2:  Sensores y reloj                                      | Ethernet
    fila 3:  Salidas a los modulos: buffers 74HCT245 y conectores HUB12 / HUB75
"""

MARCOS = [   # (titulo, x0, y0, x1, y1)
    ('Alimentación 9-36 V', 12.7, 12.7, 175.26, 152.4),
    ('ESP32-S3 DevKitC-1', 179.07, 12.7, 290.83, 152.4),
    ('Entradas, relés y expansor MCP23017', 294.64, 12.7, 497.84, 152.4),
    ('RS485 / Modbus', 501.65, 12.7, 581.66, 152.4),
    ('Sensores, reloj y medición', 12.7, 156.21, 433.07, 238.76),
    ('Ethernet W5500', 436.88, 156.21, 581.66, 238.76),
    ('Salidas a los módulos: buffers 74HCT245 y conectores HUB12 / HUB75', 12.7, 242.57, 581.66, 373.38),
]

TEXTO = {'J12': 'abajo-izq', 'D10': 'derecha', 'D11': 'derecha'}

PUERTOS = {
    # RS485
    'RS485_RX': (518.16, 48.26, 'izq'), 'RS485_TX': (518.16, 55.88, 'izq'), 'RS485_DE': (518.16, 63.5, 'izq'),
    # reloj / I2C
    'SCL': (27.94, 195.58, 'izq'), 'SDA': (27.94, 198.12, 'izq'),
    # sensores
    'ONEWIRE': (139.7, 220.98, 'izq'), 'ADC_LUZ': (220.98, 203.2, 'izq'), 'ADC_VLED': (309.88, 203.2, 'izq'),
    # ethernet
    'ETH_CS': (533.4, 198.12, 'der'),
    # bus de LEDs
    'LED_D0': (35.56, 273.05, 'izq'), 'LED_D1': (35.56, 275.59, 'izq'), 'LED_D2': (35.56, 278.13, 'izq'),
    'LED_D3': (35.56, 280.67, 'izq'), 'LED_D4': (35.56, 283.21, 'izq'), 'LED_D5': (35.56, 285.75, 'izq'),
    'LED_CLK': (132.08, 273.05, 'izq'), 'LED_LAT': (132.08, 275.59, 'izq'), 'LED_OE': (132.08, 278.13, 'izq'),
    'LED_A': (132.08, 280.67, 'izq'), 'LED_B': (132.08, 283.21, 'izq'), 'LED_C': (132.08, 285.75, 'izq'),
    'LED_D': (132.08, 288.29, 'izq'), 'LED_E': (132.08, 290.83, 'izq'),
}


def plantilla():
    pos = {}

    def P(ref, x, y, rot=0, esp=None):
        pos[ref] = (x, y, rot, esp)

    # ---------------- ESP32
    P('U1', 234.95, 69.85)
    P('SW1', 234.95, 116.84)
    for n, ref in enumerate(('H1', 'H2', 'H3', 'H4')):
        P(ref, 198.12 + 20.32 * n, 137.16)

    # ---------------- Alimentacion: entrada a la izquierda, 5 V a la derecha
    P('J1', 22.86, 40.64, 0, 'y')
    P('J2', 22.86, 60.96)
    P('F1', 45.72, 40.64, 90)
    P('D1', 60.96, 40.64, 180)
    P('D2', 73.66, 48.26, 270)
    P('C1', 83.82, 48.26)
    P('U2', 111.76, 45.72)
    P('L1', 137.16, 48.26, 90)
    P('D3', 129.54, 58.42, 270)
    P('C2', 152.4, 55.88)
    P('D4', 40.64, 91.44, 180)
    P('R1', 81.28, 87.63)
    P('D5', 81.28, 99.06, 90)
    for n, (ref, red) in enumerate((('#FLG01', '+VIN'), ('#FLG02', 'GND'), ('#FLG03', '+5V'), ('#FLG04', '+3V3'),
                                    ('#FLG05', '+5V_DK'))):
        P(ref, 30.48 + 22.86 * n, 132.08, 0 if red == 'GND' else 180)

    # ---------------- Entradas, reles y expansor
    P('U6', 342.9, 81.28)                    # MCP23017: I2C a la izquierda, GPB/GPA a la derecha
    P('C6', 330.2, 33.02)
    P('R5', 313.69, 76.2, 180)               # RESET a +3V3
    P('U9', 406.4, 66.04)                    # ULN2003A
    # reles: bobina a la izquierda (+5V arriba), contactos a la derecha, bornera en la orilla
    for (k, led, rl, j), y0 in ((('K1', 'R10', 'D8', 'J9'), 40.64), (('K2', 'R11', 'D9', 'J10'), 71.12)):
        P(k, 452.12, y0, 0, 'x')
        P(led, 429.26, y0 - 3.81)
        P(rl, 429.26, y0 + 7.62, 90)
        P(j, 480.06, y0)
    P('J11', 480.06, 91.44)                  # ventilador
    # entradas optoaisladas: la bornera en la orilla derecha, la senal va hacia el expansor (derecha -> izquierda)
    for k, (c, rpu, u, d, rin) in enumerate((('C7', 'R7', 'U7', 'D6', 'R6'), ('C8', 'R9', 'U8', 'D7', 'R8'))):
        yc = 104.14 + 22.86 * k
        P(c, 391.16, yc + 3.81)
        P(rpu, 398.78, yc - 3.81, 180)
        P(u, 414.02, yc + 2.54, 0, 'y')
        P(d, 429.26, yc + 3.81, 270)
        P(rin, 441.96, yc, 270)
    P('J8', 480.06, 119.38)
    P('JP3', 457.2, 139.7, 90)

    # ---------------- RS485
    P('U10', 543.56, 50.8)
    P('C9', 530.86, 30.48)
    P('R12', 525.78, 67.31)
    P('R13', 551.18, 82.55)
    P('JP4', 551.18, 96.52, 270)
    P('D10', 563.88, 88.9, 270)
    P('D11', 563.88, 114.3, 270)
    P('J12', 574.04, 63.5)

    # ---------------- Sensores, reloj y medicion
    P('R17', 38.1, 189.23, 180)              # SCL a +3V3
    P('R16', 45.72, 191.77, 180)             # SDA a +3V3
    P('J18', 35.56, 226.06, 0, 'y')          # expansion I2C
    P('Y1', 53.34, 204.47, 270)
    P('U11', 73.66, 200.66)
    P('C11', 90.17, 213.36)
    P('D12', 91.44, 180.34)
    P('J14', 106.68, 180.34)
    P('#FLG06', 82.55, 175.26)
    P('#FLG07', 97.79, 172.72)
    P('U12', 152.4, 203.2)
    P('R18', 167.64, 196.85, 180)
    P('J15', 190.5, 205.74)
    P('C12', 233.68, 207.01)
    P('R20', 246.38, 203.2, 270)
    P('R19', 256.54, 207.01)
    P('J16', 275.59, 200.66)
    P('C13', 322.58, 207.01)
    P('R22', 332.74, 207.01)
    P('R21', 345.44, 203.2, 270)
    P('J17', 363.22, 203.2)

    # ---------------- Ethernet
    P('J13', 480.06, 200.66)
    P('R15', 444.5, 196.85, 180)
    P('C10', 454.66, 204.47)
    P('R14', 510.54, 191.77, 180)
    P('H5', 497.84, 226.06)
    P('H6', 513.08, 226.06)

    # ---------------- Salidas: datos (U3), control grupo A (U4) y grupo B (U5); conectores en fila
    P('U3', 63.5, 285.75)
    P('C3', 88.9, 259.08, 90)
    P('RN1', 88.9, 283.21, 270)
    P('U4', 170.18, 285.75)
    P('C4', 195.58, 259.08, 90)
    P('RN2', 195.58, 283.21, 270)
    P('U5', 170.18, 345.44)
    P('C5', 195.58, 320.04, 90)
    P('RN3', 195.58, 342.9, 270)
    P('R2', 40.64, 317.5, 180)               # LED_EN a +5V: buffers apagados al arrancar
    P('R3', 226.06, 350.52)                  # HB_OE a GND
    P('R4', 233.68, 297.18)                  # HA_OE al puente de reposo
    P('JP1', 233.68, 307.34, 180)
    P('J3', 289.56, 304.8)                   # HUB75
    P('JP2', 316.23, 304.8, 180)             # E (pin 8 del HUB75)
    for n, ref in enumerate(('J4', 'J5', 'J6', 'J7')):
        P(ref, 370.84 + 54.61 * n, 304.8)
    return pos
