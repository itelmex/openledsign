# Interfaz ESP32 → módulos P10 (HUB12)

Notas del 11 nov 2026, para el **prototipo de banco** (fase 1): ESP32-S3 de repuesto + 74HCT245 en
placa perforada + 10 P10. La tarjeta OpenLed final usa el mismo principio con 4 salidas HUB12 y 1 HUB75
(ver `02-proposito-general/LEEME.md`).

## 1. Conector HUB12 (IDC de 16 pines, 2×8)

| Pin | Señal | Pin | Señal |
|---|---|---|---|
| 1 | **OE** (encender / brillo) | 2 | **A** (fila) |
| 3 | GND | 4 | **B** (fila) |
| 5 | GND | 6 | C (no se usa en 1/4) |
| 7 | GND | 8 | **CLK** |
| 9 | GND | 10 | **LAT / STB** |
| 11 | GND | 12 | **R** (datos) |
| 13 | GND | 14 | G (bicolor) |
| 15 | GND | 16 | D (no se usa en 1/4) |

Cada P10 tiene un conector de **entrada** y otro de **salida**, que van encadenados.
Es el pinout más común, pero **hay que confirmarlo con el multímetro**: los GND deben tener continuidad
con el GND de la bornera de alimentación del módulo.

## 2. Por qué hace falta el 74HCT245

La ESP32 saca 3.3 V. La entrada del P10 es un 74HC245 a 5 V, que necesita al menos 3.5 V para leer un "1".
Con 3.3 V a veces funciona y a veces no (píxeles locos, parpadeo). El **74HCT245** a 5 V acepta
2.0 V como "1" y saca 5 V limpios.

## 3. Esquema del prototipo

```
 ESP32-S3                 74HCT245 (VCC = 5 V)                       HUB12 → P10 #1
 ─────────                ─────────────────────                      ─────────────
 GPIO4  (A)   ──────────► A1        B1 ──[33Ω]─────────────────────► 2  A
 GPIO5  (B)   ──────────► A2        B2 ──[33Ω]─────────────────────► 4  B
 GPIO6  (CLK) ──────────► A3        B3 ──[33Ω]─────────────────────► 8  CLK
 GPIO7  (LAT) ──────────► A4        B4 ──[33Ω]─────────────────────► 10 LAT
 GPIO15 (OE)  ──────────► A5        B5 ──[33Ω]─────────────────────► 1  OE
 GPIO16 (R1)  ──────────► A6        B6 ──[33Ω]─────────────────────► 12 R
 GPIO17 (R2)  ──────────► A7        B7 ──[33Ω]──► 2ª cadena (opcional)
                    GND ─► A8        B8 ── (libre)
                          DIR (1)  ── 5 V   (sentido A → B)
                          OE# (19) ── GND   (siempre activo)
                          VCC (20) ── 5 V + 100 nF a GND
                          GND (10) ── GND ─────────────────────────► 3,5,7,9,11,13,15  GND
```

- **33–47 Ω en serie** en cada salida (sobre todo CLK) para evitar rebotes en el cable plano.
- **10 kΩ de OE a GND** del lado de 5 V, para que el letrero quede apagado mientras arranca.
- Estos pines son los del prototipo y evitan los de arranque (0, 3, 45, 46), USB (19, 20),
  flash (26–32) y PSRAM octal (33–37). La tarjeta final usa la asignación de `02-proposito-general`.
- Cable plano IDC de 16 hilos, **50 cm o menos** hasta el primer módulo.

## 4. Alimentación

- **Módulos**: fuente de 5 V propia (40 A para 10 P10), conectada **a la bornera de cada módulo**
  o de cada par de módulos con cable de 1.5–2.5 mm². Nunca por el cable plano.
- **Tarjeta**: en OpenLed, una fuente **exclusiva** de 9–36 V con buck a 5 V. En el prototipo,
  el USB de la DevKit y el 74HCT245 desde los 5 V de los módulos (o un regulador aparte).
- **Tierra común** entre la tarjeta y la fuente de los módulos: obligatoria.

## 5. Ciclo de barrido del firmware (escaneo 1/4)

```
para cada fase f = 0..3:
   1. mandar por DMA los 128 bits × N módulos de la fase f   (R + CLK)
   2. OE = apagado                     (evita "fantasmas")
   3. A,B = f                          (filas f, f+4, f+8, f+12)
   4. pulso en LAT                     (los 74HC595 toman los datos)
   5. OE = encendido con PWM           (brillo)
```

- **Orden de bits**: el P10 no va fila por fila, sino en bloques de 8 píxeles entrelazando 4 filas,
  y cambia según el fabricante. El firmware usa una tabla de mapeo y un patrón de prueba para ajustarlo.
- **Polaridad**: en muchos P10 el LED enciende con R = 0, y OE puede ser activo alto o bajo.
  Las dos cosas son opciones de configuración.

## 6. Letrero de 5×2 (160×32)

Una sola cadena de 10 módulos en "S": la salida del módulo 5 (arriba a la derecha) va a la entrada
del 6 (abajo a la derecha), y la fila de abajo se recorre de derecha a izquierda. El firmware reacomoda la imagen.

## 7. Material del prototipo

| Pieza | Cant. |
|---|---|
| ESP32-S3 (la de repuesto, MAC e0:72:a1:d6:63:a0) | 1 |
| 74HCT245 (DIP-20) + base | 1 |
| Resistencias 33 Ω / 10 kΩ | 7 / 1 |
| Capacitores 100 nF / 470 µF 10 V | 1 / 1 |
| Conector IDC macho 2×8 + cable plano 16 hilos ≤ 50 cm | 1 |
| Fuente 5 V 40 A (módulos) | 1 |
| Cable 1.5–2.5 mm² rojo/negro, terminales | — |
