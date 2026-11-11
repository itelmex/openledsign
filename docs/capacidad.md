# ¿Cuántos módulos maneja un ESP32?

Son cálculos (11 nov 2026), todavía sin probar.

## P10 de un color (HUB12, 32×16, escaneo 1/4)

- 512 LEDs × 1 bit = **64 bytes por módulo**. La memoria no limita: 500 módulos son 32 KB.
- El P10 se refresca en 4 fases. En cada fase hay que mandar **128 bits por módulo** de la cadena.
- Fórmula: `N_max = reloj / (4 fases × refresco × 128 bits)`

| Reloj | 100 Hz | 200 Hz (sin parpadeo) | 400 Hz (bien en video de celular) |
|---|---|---|---|
| 5 MHz | ~97 | ~48 | ~24 |
| 10 MHz | ~195 | ~97 | ~48 |

- Con DMA (periférico LCD_CAM del S3) la CPU queda libre para WiFi, MQTT y la web.
- En cadenas largas el reloj práctico es de 5 a 10 MHz. Una cadena cómoda tiene **20 a 40 módulos**.
- Con **cadenas en paralelo** (reloj, latch y filas compartidos; una línea de datos por cadena)
  se llega a cientos de módulos. OpenLed trae 4 salidas HUB12, unos 300 P10 a 200 Hz.
- 10 módulos (letrero de 160×32): una cadena basta, con más de 1000 Hz de refresco a 10 MHz.

## Qué limita en la práctica

1. **Corriente**: un P10 rojo puede pedir 3–4 A a 5 V con todo encendido; con texto normal, 0.5–1 A.
   Se reparte en varias fuentes de 5 V (40–60 A cada una), con las tierras unidas.
2. **Distancia**: de la controladora al primer módulo, 1–2 m como máximo. Entre módulos no hay
   problema, porque cada uno vuelve a amplificar la señal.
3. **Brillo**: se ajusta con OE (PWM) sin perder velocidad, porque los datos de la siguiente fase
   se cargan mientras se ve la actual.

## Color (HUB75)

El límite depende de la profundidad de color (bits por canal) y del refresco. Como referencia,
una docena de módulos de 64×32 con buen color por tarjeta. Para letreros más grandes, varias
tarjetas sincronizadas por red.
