# OpenLed Rev A: esquemático (KiCad)

11 nov 2026. **Primera versión, para revisar.** Todavía no hay PCB ni prototipo.

| Archivo | Qué es |
|---|---|
| `openled_esquematico.pdf` | El esquemático en PDF (hoja A2) |
| `openled.kicad_pro`, `openled.kicad_sch` | Proyecto KiCad. Se abre con KiCad 7 o posterior; KiCad 10 lo convierte al guardar |
| `openled.kicad_sym`, `openled.pretty/` | Librería propia: DevKit ESP32-S3 en zócalo y módulo W5500 |
| `generador/` | Scripts que generan el esquemático: `diseno_openled.py` (piezas y conexiones) y `plantilla_openled.py` (acomodo a mano) |

Se generó con el mismo generador y el mismo estilo que la tarjeta de entrada de OpeniPark: una hoja, bloques con marco,
cables reales dentro de cada bloque, etiquetas en los pines de la ESP32 y un puerto en la orilla de cada bloque.

## Bloques

| Bloque | Contenido |
|---|---|
| Alimentación 9-36 V | Bornera y jack 5.5×2.1 en paralelo, PTC 1.1 A, 1N5822 contra polaridad invertida, TVS P6KE43A, buck **LM2596T-5.0** (TO-220, 33 µH, 1N5822), 1N5819 al 5V de la DevKit, LED |
| ESP32-S3 DevKitC-1 | En zócalo; botón PRUEBA en GPIO0; 4 barrenos M3 |
| Entradas, relés y expansor | **MCP23017** (I2C 0x20). 2 entradas con PC817 y común a GND o +VIN por puente. **ULN2003A**: relé 1, relé 2 (opcional) y ventilador de 5 V. GPB3 = `LED_EN` (enciende los buffers) |
| RS485 / Modbus | MAX3485 a 3.3 V, DE con 10k a GND (arranca recibiendo), terminación de 120 Ω por puente, TVS P6KE6.8CA |
| Sensores, reloj y medición | DS1307 + cristal + pila CR2032 externa; DS18B20 en la tarjeta + bornera para una sonda (mismo bus 1-Wire); fotorresistencia (bornera) al ADC; medición de los 5 V de los módulos (divisor 10k/10k); conector I2C de expansión (JST-XH) |
| Ethernet W5500 | Módulo azul en tira 2×5, alimentado a 5 V, reset por RC, CS con 10k a 3.3 V |
| Salidas a los módulos | 3 × **74HCT245** (3.3 V → 5 V) + 3 redes de resistencias de 33 Ω ×8 (DIP-16, 4116R-1-330). U3: datos D0-D5; U4: control del grupo A (HUB75, HUB12 #1, #2); U5: control del grupo B (HUB12 #3, #4). 5 conectores IDC 2×8 |

## Pines del ESP32-S3

| GPIO | Señal | GPIO | Señal |
|---|---|---|---|
| 4, 5, 6, 7, 15, 16 | LED_D0 … LED_D5 | 14, 21, 47, 38 | SPI SCK, MOSI, MISO, ETH_CS |
| 17, 18, 8 | LED_CLK, LED_LAT, LED_OE | 39, 40, 46 | RS485 TX, RX, DE |
| 9, 10, 11, 12, 13 | LED_A … LED_E | 41, 42 | SDA, SCL |
| 3 | 1-Wire (DS18B20) | 1, 2 | ADC: 5 V de los módulos, luz |
| 0 | Botón PRUEBA | 48 | LED RGB de la DevKit (estado) |

Libres: 43/44 (UART0, depuración), 19/20 (USB). Se evitan 35-37 (PSRAM octal) y 45 (strap del voltaje de la flash).

## Decisiones de esta versión

- **Arranque seguro de los módulos:** los tres 74HCT245 arrancan apagados (CE con 10k a +5V) hasta que el firmware baja `LED_EN`.
  OE del grupo B tiene 10k a GND. El de grupo A va a GND o a 5 V con el puente **JP1** («OE en reposo»):
  GND para P10 HUB12 (OE activo en alto) y 5 V para HUB75 (OE activo en bajo).
- **Pin 8 del HUB75 (E):** pasa por el puente **JP2**. Ciérralo solo con paneles de 64 filas; en muchos paneles ese pin es GND.
- **Bicolor:** HUB12 #1 y #2 llevan G (D4 y D5). Las salidas #3 y #4 son de un color.
- **Las redes ya con resistencia (HD_*, HA_*, HB_*) llevan etiqueta en cada pin**, en lugar de cables: cada una va a 2 o 3 conectores.
  Lo mismo `LED_EN` (sale del expansor) y SDA/SCL del MCP23017.
- **ETH_CS en GPIO38:** en la DevKit oficial v1.1 ese pin es el LED RGB (parpadeará). Las DevKit clon N16R8 lo tienen en GPIO48.
- **ULN2003A a 3.3 V:** con las salidas push-pull del MCP23017 entra ~0.7 mA, suficiente para relés de ~70 mA y un ventilador de 5 V chico.

## Cómo se comprobó

- `python3 generador/esquematico.py` genera la hoja, exporta la netlist con **KiCad 10** (flatpak) y la compara pin por pin con `diseno_openled.py`:
  **0 diferencias en 113 redes**, 0 conexiones sin trazar y 0 textos encimados.
  (El `kicad-cli` 7 del sistema da falsos «sin conectar» en algunos pines; por eso se usa el de KiCad 10.)
- ERC de KiCad 10: solo avisos de librerías no configuradas en la consola y 3 de «pin triestado unido a GND»
  (entradas sin usar de los 74HCT245, a propósito).

## Pendiente antes de la PCB

1. Confirmar con el multímetro el pinout HUB12 y la polaridad de OE de los P10 reales (prototipo de banco).
2. Elegir entre 1 o 2 relés (el 2 está dibujado como opcional).
3. Revisar cada huella contra la pieza real: inductor de 33 µH 3 A, jack, PTC de 60 V, borneras, relés, red de resistencias DIP-16.
4. Medir la DevKit (filas a 25.40 mm o 22.86 mm) y el módulo W5500, como en la tarjeta de entrada.
