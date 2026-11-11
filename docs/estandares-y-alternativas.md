# Estándares y alternativas para letreros de LED

Notas del 11 nov 2026: punto de partida del proyecto.

## Problema

Luis tiene una tarjeta Huidu **HD-U6A** y 10 módulos **P10** de un color. La HD-U6A solo se programa
con **HD2018/HD2020**, que corren en Windows y se conectan por USB. En Linux, bajo Wine, HD2018 abre
pero da errores y se traba. Además, ninguna tarjeta comercial barata muestra datos en vivo
(por ejemplo, los lugares libres de OpeniPark).

## ¿Hay un estándar?

No hay uno universal. Hay tres niveles:

1. **Conexión de los módulos (estándar de hecho)**: **HUB12** (un color) y **HUB75** (color).
   Cualquier controladora sirve con cualquier módulo de ese tipo. Hay librerías abiertas:
   DMD/DMD2 (P10 HUB12), ESP32-HUB75-MatrixPanel-DMA y rpi-rgb-led-matrix.
2. **Tarjetas comerciales (cada marca tiene su protocolo)**: Huidu (HD2018 / HDPlayer / LedArt),
   Onbon BX (LedShow), Lingsheng, Xixun… Algunas publican un SDK, pero sigue siendo de su marca.
   Antes existía el **protocolo Alpha** (Adaptive Micro Systems), hoy casi en desuso.
3. **Tránsito y estacionamientos (estándares formales)**:
   - **NTCIP 1203** (EE. UU.): letreros de mensaje variable y guía de estacionamiento. El formato
     del mensaje usa el lenguaje **MULTI** (`[jl3]` centrar, `[fo2]` fuente, `[np]` página nueva). Va sobre SNMP.
   - **EN 12966** (Europa): solo la parte física (visibilidad, colores), no la comunicación.
   - **DATEX II** (Europa): intercambio de datos de tráfico y ocupación de estacionamientos.
   - Son pesados y las tarjetas baratas no los soportan.

## Alternativas evaluadas

| Opción | Ventaja | Desventaja |
|---|---|---|
| HD-U6A + HD2018 en Wine | ya se tiene | inestable; no muestra datos en vivo |
| HD-U6A + Windows en VirtualBox | HD2018 funciona | engorroso; no muestra datos en vivo |
| Tarjeta Huidu WiFi (serie HD-W) + app LedArt | sencillo desde el celular, barato | no se integra con nada; protocolo cerrado |
| ESP32-S3 OTG hablando con la HD-U6A | — | no se puede: las dos son "anfitrión" USB; el formato de archivos es propietario |
| **Controladora propia ESP32-S3 → HUB12/HUB75** | datos en vivo, navegador, abierta, se integra con todo | hay que diseñarla (este proyecto) |

## Decisión

Hacer **OpenLed**: una controladora propia, **abierta (GPL-3.0)** y de **propósito general**.
Su API propia es MQTT/HTTP/Modbus con JSON, y opcionalmente acepta mensajes **MULTI** (NTCIP 1203)
para tomar un estándar conocido sin cargar con todo NTCIP.
