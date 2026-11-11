# OpenLed

**Controlador abierto de letreros de LED** (HUB12 y HUB75) basado en ESP32-S3, para cualquier
aplicación: estacionamientos, turnos, precios, andon industrial, publicidad, avisos, marcadores…

> Estado: **diseño / exploración** (11 nov 2026). Todavía no hay hardware fabricado ni firmware probado.
> El nombre "OpenLed" está sujeto a la búsqueda de marca en el IMPI. Repositorio: https://github.com/itelmex/openledsign

## Qué es

- **Hardware estándar**: ESP32-S3 (DevKitC-1 N16R8), 4 salidas HUB12 + 1 HUB75, Ethernet (W5500),
  WiFi, RS485 / Modbus, reloj de tiempo real, sensores de temperatura y luz, 2 entradas
  optoaisladas, relé, monitor de la fuente de los módulos y protecciones. Se alimenta con una fuente
  exclusiva de 9–36 V.
- **De 1 a N módulos**: un color, bicolor o color, configurado desde el navegador (tamaño, escaneo,
  orden de bits, cadenas, giro). Con 4 salidas, una tarjeta puede manejar un letrero grande o 4 letreros distintos.
- **Cualquier diseño de mensaje**: programa → páginas → zonas → elementos (texto, variables,
  reloj, imágenes, GIF, iconos, barras, QR) con efectos, horarios, condiciones y prioridades.
  Fuentes TTF convertidas en el navegador y vista previa en vivo.
- **Cualquier fuente de datos**: MQTT (cualquier broker), HTTP (cliente y API REST), Modbus RTU/TCP,
  protocolo serie de texto, entradas locales, sensores y fórmulas. Perfiles listos para
  [OpeniPark](https://openipark.com), Home Assistant, turnos y andon.
- Opcional: mensajes en formato **MULTI de NTCIP 1203**.

## Contenido

| Carpeta / archivo | Qué es |
|---|---|
| `02-proposito-general/LEEME.md` | **Diseño vigente**: hardware, pines, firmware, costos, fases y decisiones |
| `01-exploracion/LEEME.md` | Primera exploración (orientada solo a OpeniPark); se conserva como historial |
| `docs/estandares-y-alternativas.md` | Por qué una controladora propia: estándares (HUB12/HUB75, NTCIP, MULTI) y alternativas comerciales |
| `docs/capacidad.md` | Cuántos módulos maneja un ESP32 y qué lo limita |
| `docs/interfaz-hub12.md` | Conexión ESP32 → P10 en detalle y prototipo de banco |

Cada alternativa de diseño va en su propia subcarpeta numerada; las anteriores no se borran.

## Fases

1. Prototipo de banco: ESP32-S3 + 74HCT245 + 10 P10 (y un módulo HUB75 para probar color).
2. Motor de mensajes + editor web + API.
3. Esquemático y PCB Rev A.
4. Perfiles de aplicación (OpeniPark, turnos, andon, Home Assistant).
5. MULTI, Modbus TCP, varias tarjetas sincronizadas, editor de flota.

## Autor

Luis ([@itelmex](https://github.com/itelmex)), creador de OpeniPark.

## Créditos

Este proyecto se apoyará en trabajo abierto de otros, que se acreditará conforme se use:
- [ESP32-HUB75-MatrixPanel-DMA](https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA) (MIT): referencia para el manejo de HUB75 por DMA en ESP32-S3.
- [DMD2](https://github.com/freetronics/DMD2) (Freetronics): referencia para el manejo de P10 HUB12.
- Espressif ESP-IDF / Arduino-ESP32.

## Licencia

Firmware y software: **GNU GPL v3.0** (ver `LICENSE`). La licencia del hardware (esquemático y PCB) se definirá más adelante.
