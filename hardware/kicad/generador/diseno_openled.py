"""OpenLed Rev A: controlador abierto de letreros de LED (HUB12 x4 + HUB75) con ESP32-S3 DevKitC-1 en zocalo.

Todo de agujero pasante (se arma en casa). Lista de piezas y conexiones: cada pieza es (ref, simbolo, valor, huella,
{pin: red}, bloque). Diseno descrito en ../../../02-proposito-general/LEEME.md.

Bus de LEDs: 14 lineas del ESP32 (LCD_CAM + DMA) -> 3 buffers 74HCT245 a 5 V -> 33 ohm -> conectores.
  U2: datos D0-D5 (a HUB75 y a los cuatro HUB12)
  U3: control del grupo A (CLK LAT OE A B C D E) -> HUB75, HUB12 #1 y #2
  U4: control del grupo B (CLK LAT OE A B C D)   -> HUB12 #3 y #4
Los buffers arrancan apagados (CE en alto por 10k) hasta que el firmware pone LED_EN en bajo (MCP23017 GPB3).
"""
from comun import Lista, FP, W5500

TITULO = 'OpenLed - controlador de letreros LED Rev A'
HOJA = ('A2', 594.0, 420.0)
PLANTILLA = 'plantilla_openled'
ETIQUETAR_EN = 'U1'
REVISION = 'A'
COMENTARIOS = ['ESP32-S3 en zocalo; 4x HUB12 + HUB75; Ethernet; RS485; reloj; sensores.',
               'Fuente exclusiva 9-36 V; la de los modulos solo se mide. Tierra comun obligatoria.',
               'Mismo nombre de etiqueta = misma red. github.com/itelmex/openledsign (GPL-3.0)',
               'Generado: hardware/kicad/generador (diseno_openled + plantilla_openled)']
HOJAS = [('fuente', 'Alimentacion'), ('esp32', 'ESP32-S3'), ('buffers', 'Buffers'), ('hub', 'Conectores HUB'),
         ('es', 'Entradas, reles y expansor'), ('com', 'Comunicacion'), ('sensores', 'Sensores y reloj')]
POTENCIA = {'GND': 'power:GND', '+3V3': 'power:+3V3', '+5V': 'power:+5V', '+VIN': None, '+5V_DK': None}

# Redes con etiqueta en cada pin: el bus ya con resistencia se reparte a 5 conectores; LED_EN viene del expansor.
ETIQUETAR_REDES = {'LED_EN'} | {'HD_D%d' % k for k in range(6)} | \
    {'HA_' + s for s in ('CLK', 'LAT', 'OE', 'A', 'B', 'C', 'D', 'E')} | {'HB_' + s for s in ('CLK', 'LAT', 'OE', 'A', 'B', 'C', 'D')}
ETIQUETAR_PINES = {('U6', '13'), ('U6', '12')}     # SDA y SCL del expansor (el bus I2C se cablea en el bloque del reloj)
LARGO_ETIQUETA = {('U3', '19'): 9, ('U4', '19'): 9, ('U5', '19'): 9, ('J3', '6'): 9}   # librar el +5V de DIR y el GND del HUB75

L = Lista()
partes = L.partes
FP_IDC16 = FP['IDC'].format(n=8)

# ---------------- ESP32-S3 DevKitC-1 (pin de la tira: red). GPIO entre parentesis.
h = 'esp32'
DEVKIT = {1: '+3V3', 2: '+3V3',          # 3V3 sale del regulador de la DevKit
          4: 'LED_D0',     # GPIO4
          5: 'LED_D1',     # GPIO5
          6: 'LED_D2',     # GPIO6
          7: 'LED_D3',     # GPIO7
          8: 'LED_D4',     # GPIO15
          9: 'LED_D5',     # GPIO16
          10: 'LED_CLK',   # GPIO17
          11: 'LED_LAT',   # GPIO18
          12: 'LED_OE',    # GPIO8
          13: 'ONEWIRE',   # GPIO3
          14: 'RS485_DE',  # GPIO46 (10k a GND: arranca recibiendo)
          15: 'LED_A',     # GPIO9
          16: 'LED_B',     # GPIO10
          17: 'LED_C',     # GPIO11
          18: 'LED_D',     # GPIO12
          19: 'LED_E',     # GPIO13
          20: 'SPI_SCK',   # GPIO14
          21: '+5V_DK', 22: 'GND', 23: 'GND',
          26: 'ADC_VLED',  # GPIO1 (ADC1)
          27: 'ADC_LUZ',   # GPIO2 (ADC1)
          28: 'SCL',       # GPIO42
          29: 'SDA',       # GPIO41
          30: 'RS485_RX',  # GPIO40
          31: 'RS485_TX',  # GPIO39
          32: 'ETH_CS',    # GPIO38 (en la DevKit oficial v1.1 es el LED RGB: parpadea, no estorba)
          36: 'BOTON',     # GPIO0 (BOOT): boton de prueba
          39: 'SPI_MISO',  # GPIO47
          40: 'SPI_MOSI',  # GPIO21
          43: 'GND', 44: 'GND'}
L.P('U', 'openled:ESP32-S3-DevKitC-1', 'ESP32-S3 DevKitC-1 N16R8', 'openled:ESP32-S3-DevKitC-1_Zocalo', DEVKIT, h)
L.P('SW', 'Switch:SW_Push', 'PRUEBA', 'Button_Switch_THT:SW_PUSH_6mm', {1: 'BOTON', 2: 'GND'}, h)
L.agujeros(h)

# ---------------- Alimentacion: 9-36 V -> PTC -> diodo de polaridad -> TVS -> LM2596T-5.0 -> +5V
h = 'fuente'
L.borne(['VIN_EXT', 'GND'], h, 'Fuente 9-36 V (+ -)', 5.08)
L.P('J', 'Connector:Barrel_Jack', 'Jack 5.5x2.1 (centro +)', 'Connector_BarrelJack:BarrelJack_Horizontal',
    {1: 'VIN_EXT', 2: 'GND'}, h)
L.P('F', 'Device:Polyfuse', 'PTC 1.1A 60V (MF-R110)', 'Fuse:Fuse_Bourns_MF-RHT1100', {1: 'VIN_EXT', 2: 'VIN_F'}, h)
L.D('1N5822', '+VIN', 'VIN_F', h, FP['D41'], sym='Device:D_Schottky')     # polaridad invertida
L.D('P6KE43A', '+VIN', 'GND', h, FP['D15'], sym='Device:D_TVS')            # 36.8 V sin conducir
L.CP('100uF 50V', '+VIN', 'GND', h, FP['CP6'])
reg = L.P('U', 'Regulator_Switching:LM2596T-5', 'LM2596T-5.0', 'Package_TO_SOT_THT:TO-220-5_P3.4x3.7mm_StaggerOdd_Lead3.8mm_Vertical',
          {1: '+VIN', 2: 'SW_BUCK', 3: 'GND', 4: '+5V', 5: 'GND'}, h)
L.D('1N5822', 'SW_BUCK', 'GND', h, FP['D41'], sym='Device:D_Schottky')
L.P('L', 'Device:L', '33uH 3A', 'Inductor_THT:L_Radial_D12.0mm_P5.00mm_Fastron_11P', {1: 'SW_BUCK', 2: '+5V'}, h)
L.CP('220uF 10V', '+5V', 'GND', h, FP['CP6'])
L.D('1N5819', '+5V_DK', '+5V', h, FP['D41'], sym='Device:D_Schottky')      # al 5V de la DevKit (no regresa por su USB)
L.R('1k', '+5V', 'LED_PWR', h)
L.P('D', 'Device:LED', 'LED 5V', FP['LED'], {1: 'GND', 2: 'LED_PWR'}, h)
for r in ['+VIN', 'GND', '+5V', '+3V3', '+5V_DK']:
    L.flag(r, h)

# ---------------- Buffers 74HCT245 (3.3 V -> 5 V): A->B fijo, CE por LED_EN (10k a +5V: apagados al arrancar)
h = 'buffers'
SAL_DATOS = ['LED_D0', 'LED_D1', 'LED_D2', 'LED_D3', 'LED_D4', 'LED_D5', None, None]
SAL_A = ['LED_CLK', 'LED_LAT', 'LED_OE', 'LED_A', 'LED_B', 'LED_C', 'LED_D', 'LED_E']
SAL_B = ['LED_CLK', 'LED_LAT', 'LED_OE', 'LED_A', 'LED_B', 'LED_C', 'LED_D', None]
SALIDA_DE = {}    # (buffer, entrada) -> red de salida ya con su resistencia


def buffer(entradas, prefijo):
    """74HCT245 + red de 8 resistencias de 33 ohm aisladas (DIP-16): resistencia k entre los pines k+1 y 16-k."""
    pines = {1: '+5V', 10: 'GND', 19: 'LED_EN', 20: '+5V'}
    red_r = {}
    for k, e in enumerate(entradas):
        pines[2 + k] = e if e else 'GND'          # entradas sin usar a GND
        if e:
            nb, ns = '%s_%s_B' % (prefijo, e[4:]), '%s_%s' % (prefijo, e[4:])
            pines[18 - k] = nb
            red_r[k + 1], red_r[16 - k] = nb, ns
            SALIDA_DE[(prefijo, e)] = ns
    u = L.P('U', '74xx:74HC245', '74HCT245', 'Package_DIP:DIP-20_W7.62mm', pines, h)
    L.C('100nF', '+5V', 'GND', h, cerca=u)
    L.P('RN', 'Device:R_Pack08', '33 x8 (4116R-1-330)', 'Package_DIP:DIP-16_W7.62mm', red_r, h)
    return u


buffer(SAL_DATOS, 'HD')     # HD_D0..HD_D5
buffer(SAL_A, 'HA')         # HA_CLK.. HA_E
buffer(SAL_B, 'HB')         # HB_CLK.. HB_D
L.R('10k', 'LED_EN', '+5V', h)
L.R('10k', 'HB_OE', 'GND', h)                      # HUB12 #3/#4: OE en bajo = apagado mientras no hay datos
L.R('10k', 'HA_OE', 'OE_REPOSO', h)
L.P('JP', 'Jumper:Jumper_3_Open', 'OE en reposo: GND (HUB12) / 5V (HUB75)', FP['JMP3'],
    {1: 'GND', 2: 'OE_REPOSO', 3: '+5V'}, h)

# ---------------- Conectores HUB (IDC 2x8). HUB12: 1 OE, 2 A, 4 B, 6 C, 8 CLK, 10 LAT, 12 R, 14 G, 16 D; impares GND
h = 'hub'


def hub12(nombre, g, r, verde):
    pines = {1: g + '_OE', 2: g + '_A', 4: g + '_B', 6: g + '_C', 8: g + '_CLK', 10: g + '_LAT', 12: r, 14: verde,
             16: g + '_D'}
    for k in (3, 5, 7, 9, 11, 13, 15):
        pines[k] = 'GND'
    L.P('J', 'Connector_Generic:Conn_02x08_Odd_Even', nombre, FP_IDC16, pines, h)


# HUB75: 1 R1, 2 G1, 3 B1, 4 GND, 5 R2, 6 G2, 7 B2, 8 E (por puente; en muchos paneles es GND), 9 A, 10 B, 11 C, 12 D,
# 13 CLK, 14 LAT, 15 OE, 16 GND
L.P('J', 'Connector_Generic:Conn_02x08_Odd_Even', 'HUB75 (color)', FP_IDC16,
    {1: 'HD_D0', 2: 'HD_D1', 3: 'HD_D2', 4: 'GND', 5: 'HD_D3', 6: 'HD_D4', 7: 'HD_D5', 8: 'HUB75_E', 9: 'HA_A',
     10: 'HA_B', 11: 'HA_C', 12: 'HA_D', 13: 'HA_CLK', 14: 'HA_LAT', 15: 'HA_OE', 16: 'GND'}, h)
L.P('JP', 'Jumper:Jumper_2_Open', 'E: paneles de 64 filas', FP['JMP2'], {1: 'HA_E', 2: 'HUB75_E'}, h)
hub12('HUB12 #1 (bicolor)', 'HA', 'HD_D0', 'HD_D4')
hub12('HUB12 #2 (bicolor)', 'HA', 'HD_D1', 'HD_D5')
hub12('HUB12 #3', 'HB', 'HD_D2', None)
hub12('HUB12 #4', 'HB', 'HD_D3', None)

# ---------------- Entradas, reles y expansor MCP23017 (I2C 0x20)
h = 'es'
mcp = L.P('U', 'Interface_Expansion:MCP23017_SP', 'MCP23017-E/SP', 'Package_DIP:DIP-28_W7.62mm',
          {9: '+3V3', 10: 'GND', 12: 'SCL', 13: 'SDA', 15: 'GND', 16: 'GND', 17: 'GND', 18: 'MCP_RST',
           21: 'ENT1', 22: 'ENT2',                        # GPA0-1 entradas optoaisladas
           1: 'RELE1', 2: 'RELE2', 3: 'VENT', 4: 'LED_EN'}, h)   # GPB0-3
L.C('100nF', '+3V3', 'GND', h, cerca=mcp)
L.R('10k', 'MCP_RST', '+3V3', h)
for n in (1, 2):           # un PC817 por entrada; comun a GND (contacto seco, PNP) o a +VIN (NPN) por puente
    b, s, opa = 'IN%d' % n, 'ENT%d' % n, 'OPA%d' % n
    L.P('U', 'Isolator:PC817', 'PC817', 'Package_DIP:DIP-4_W7.62mm', {1: opa, 2: 'COM_E', 3: 'GND', 4: s}, h)
    L.D('1N4148', opa, 'COM_E', h)
    L.R('3.3k 1/2W', b, opa, h, FP['R2'])
    L.R('10k', s, '+3V3', h)
    L.C('100nF', s, 'GND', h)
L.P('JP', 'Jumper:Jumper_3_Open', 'Comun entradas', FP['JMP3'], {1: 'GND', 2: 'COM_E', 3: '+VIN'}, h)
L.borne(['+VIN', 'IN1', 'IN2', 'COM_E'], h, 'Entradas (+V IN1 IN2 COM)')
uln = L.P('U', 'Transistor_Array:ULN2003A', 'ULN2003A', 'Package_DIP:DIP-16_W7.62mm',
          {1: 'RELE1', 2: 'RELE2', 3: 'VENT', 8: 'GND', 9: '+5V', 16: 'K1_BOB', 15: 'K2_BOB', 14: 'VENT_K',
           4: 'GND', 5: 'GND', 6: 'GND', 7: 'GND'}, h)
for n in (1, 2):           # el rele 2 es opcional: se arma si la aplicacion lo pide
    bob = 'K%d_BOB' % n
    L.P('K', 'Relay:SANYOU_SRD_Form_C', 'SRD-05VDC-SL-C' + (' (opcional)' if n == 2 else ''),
        'Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C', {2: '+5V', 5: bob, 1: 'K%d_COM' % n, 3: 'K%d_NA' % n,
                                                         4: 'K%d_NC' % n}, h)
    L.R('1k', '+5V', 'LED_K%d' % n, h)
    L.P('D', 'Device:LED', 'LED RELE %d' % n, FP['LED'], {2: 'LED_K%d' % n, 1: bob}, h)
    L.borne(['K%d_COM' % n, 'K%d_NA' % n, 'K%d_NC' % n], h, 'Rele %d (COM NA NC)' % n, 5.08)
L.P('J', 'Connector_Generic:Conn_01x02', 'Ventilador 5V (+ -)', 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical',
    {1: '+5V', 2: 'VENT_K'}, h)

# ---------------- Comunicacion: RS485 (MAX3485 a 3.3 V) y Ethernet (modulo W5500)
h = 'com'
max485 = L.P('U', 'Interface_UART:MAX3485', 'MAX3485CPA', 'Package_DIP:DIP-8_W7.62mm',
             {1: 'RS485_RX', 2: 'RS485_DE', 3: 'RS485_DE', 4: 'RS485_TX', 5: 'GND', 6: 'RS485_A', 7: 'RS485_B',
              8: '+3V3'}, h)
L.C('100nF', '+3V3', 'GND', h, cerca=max485)
L.R('10k', 'RS485_DE', 'GND', h)
L.R('120', 'RS485_A', 'RS485_T', h)
L.P('JP', 'Jumper:Jumper_2_Open', 'Terminacion 120', FP['JMP2'], {1: 'RS485_T', 2: 'RS485_B'}, h)
L.D('P6KE6.8CA', 'RS485_A', 'GND', h, FP['D15'], sym='Device:D_TVS')
L.D('P6KE6.8CA', 'RS485_B', 'GND', h, FP['D15'], sym='Device:D_TVS')
L.borne(['RS485_A', 'RS485_B', 'GND'], h, 'RS485 (A B GND)')
# modulo azul comun (1 NC, 2 INT, 3 RST, 4 GND, 5 5V | 6 SCLK, 7 SCS, 8 MOSI, 9 MISO, 10 3.3V); se alimenta por 5V
eth = L.P('J', 'Connector_Generic:Conn_02x05_Top_Bottom', 'Modulo W5500', 'openled:Modulo_W5500',
          {3: 'ETH_RST', 4: 'GND', 5: '+5V', 6: 'SPI_SCK', 7: 'ETH_CS', 8: 'SPI_MOSI', 9: 'SPI_MISO'}, h)
L.postes(h, eth, len(W5500['barrenos']))
L.R('10k', 'ETH_CS', '+3V3', h)
L.R('10k', 'ETH_RST', '+3V3', h)                   # reset por RC al encender (no gasta GPIO)
L.CP('10uF', 'ETH_RST', 'GND', h, 'Capacitor_THT:CP_Radial_D4.0mm_P2.00mm')

# ---------------- Sensores y reloj
h = 'sensores'
L.R('4.7k', 'SDA', '+3V3', h)
L.R('4.7k', 'SCL', '+3V3', h)
rtc = L.P('U', 'Timer_RTC:DS1307+', 'DS1307+', 'Package_DIP:DIP-8_W7.62mm',
          {1: 'XT1', 2: 'XT2', 3: 'VBAT', 4: 'GND', 5: 'SDA', 6: 'SCL', 8: '+5V'}, h)
L.P('Y', 'Device:Crystal', '32.768 kHz', 'Crystal:Crystal_C26-LF_D2.1mm_L6.5mm_Horizontal', {1: 'XT1', 2: 'XT2'}, h)
L.C('100nF', '+5V', 'GND', h, cerca=rtc)
L.D('BAT85', 'VBAT', 'PILA', h, sym='Device:D_Schottky')
L.P('J', 'Connector:Screw_Terminal_01x02', 'Pila CR2032 (+ -)',
    'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-2-2.54_1x02_P2.54mm_Horizontal', {1: 'PILA', 2: 'GND'}, h)
L.flag('VBAT', h)
L.flag('PILA', h)
# temperatura: DS18B20 en la tarjeta y bornera para una sonda en el gabinete (mismo bus 1-Wire)
L.R('4.7k', 'ONEWIRE', '+3V3', h)
L.P('U', 'Sensor_Temperature:DS18B20', 'DS18B20', 'Package_TO_SOT_THT:TO-92_Inline', {1: 'GND', 2: 'ONEWIRE', 3: '+3V3'}, h)
L.borne(['+3V3', 'ONEWIRE', 'GND'], h, 'Sonda temperatura (3V3 DQ GND)')
# luz: fotorresistencia en cable (sale por una ventana del gabinete) con 10k a GND
L.borne(['+3V3', 'LDR'], h, 'Fotorresistencia')
L.R('10k', 'LDR', 'GND', h)
L.R('1k', 'LDR', 'ADC_LUZ', h)
L.C('100nF', 'ADC_LUZ', 'GND', h)
# medicion de la fuente de los modulos: divisor 10k/10k (5 V -> 2.5 V), hasta 6.6 V sin pasar de 3.3 V
L.borne(['VLED', 'GND'], h, 'Medicion 5V modulos (+ -)')
L.R('10k', 'VLED', 'ADC_VLED', h)
L.R('10k', 'ADC_VLED', 'GND', h)
L.C('100nF', 'ADC_VLED', 'GND', h)
L.P('J', 'Connector_Generic:Conn_01x04', 'I2C expansion (3V3 GND SDA SCL)', 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',
    {1: '+3V3', 2: 'GND', 3: 'SDA', 4: 'SCL'}, h)
