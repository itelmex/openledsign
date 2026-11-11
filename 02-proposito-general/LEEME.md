# OpenLed — controlador de letreros de LED de propósito general

(nombre por confirmar, ver §6; antes "TL-S3")

Luis (@itelmex) · 11 nov 2026 · Estado: **exploración** (nada fabricado ni probado)
Revisión 02 (sobre 01-exploracion): **propósito general**, **HUB75 desde la Rev A**, **firmware abierto**,
**fuente externa exclusiva para la tarjeta**.

Idea: un hardware y un software estándar para **cualquier aplicación que necesite letreros de LED**,
no solo estacionamientos. OpeniPark es una de las aplicaciones (un "perfil" de integración), no un requisito.
Misma DevKit, mismas piezas y protecciones que la tarjeta de entrada (tarjeta-openipark-s3), y un firmware
que se configura para **1 hasta N módulos** (un color, bicolor o color, HUB12 o HUB75) y permite
**cualquier diseño de mensaje**, alimentado por **cualquier fuente de datos**.
Valor frente a una tarjeta Huidu/Onbon: se maneja desde un navegador sin instalar nada (Linux, Windows,
celular), Ethernet + WiFi + RS485, API abierta y documentada, datos en vivo, monitoreo remoto, y es nuestro.

### Aplicaciones de ejemplo (todas con la misma tarjeta y el mismo firmware)

| Aplicación | Qué muestra | De dónde salen los datos |
|---|---|---|
| Estacionamientos (OpeniPark) | lugares libres por piso/zona, LLENO, flechas | MQTT de OpeniPark, lazos en las entradas |
| Turnos y filas | "TURNO A-023 → CAJA 4", tiempo de espera | botón o API HTTP del sistema de turnos |
| Gasolineras y precios | precios por producto | página web, HTTP, archivo JSON |
| Industria (andon) | meta vs. producción, paros, eficiencia | Modbus de un PLC, contador por entradas |
| Comercio y publicidad | promociones, hora, temperatura, GIF | editor web con horarios |
| Escuelas, hospitales, oficinas | avisos, reloj, llamados | MQTT / HTTP / botón |
| Eventos y deportes | marcador, cronómetro | celular (página web) o control RS485 |
| Domótica | estado de la casa, clima | Home Assistant (MQTT con autodescubrimiento) |

---

## 1. Hardware

### 1.1 Bloques

```
                 ┌─────────────────────────── OpenLed ───────────────────────────┐
 9–36 V (fuente ►│ PTC → MOSFET anti-inversión → TVS SMBJ36A → buck 5 V → DevKit │
 exclusiva de la │  (si esta fuente falla, el broker avisa por el LWT)           │
 tarjeta)        │                                                               │
 5 V módulos ───►│ bornera "medición" → divisor → ADC (solo mide, no alimenta)   │
                 │                                                               │
                 │  ESP32-S3 DevKitC-1 N16R8 (la misma de la tarjeta de entrada) │
                 │   ├─ LCD_CAM + DMA ─► 2-3× 74HCT245 ─► 4× HUB12  + 1× HUB75   │
                 │   ├─ SPI ─────────► W5500 ─► RJ45 (Ethernet)                  │
                 │   ├─ UART ────────► MAX3485 + SM712 ─► RS485 (Modbus / otros) │
                 │   ├─ I2C ─────────► PCA9555 (E/S lentas) + DS3231 (reloj)     │
                 │   ├─ 1-Wire ──────► DS18B20 (temperatura del gabinete)        │
                 │   ├─ ADC ─────────► fotorresistencia (brillo automático)      │
                 │   └─ WiFi / BLE (de la DevKit)                                │
                 │  PCA9555 ─► 2 entradas optoaisladas PC817 (contador local)    │
                 │          ─► 1 relé (cortar la fuente de 220 V de los módulos) │
                 │          ─► MOSFET ventilador 5 V · reset del W5500 · LEDs    │
                 └───────────────────────────────────────────────────────────────┘
```

### 1.2 Salidas a los módulos (lo que permite 1..N módulos)

Un solo bus paralelo de 14 líneas que genera el periférico LCD_CAM del S3 por DMA, sin usar la CPU:
6 líneas de datos (D0–D5) + CLK + LAT + OE + A, B, C, D, E.

| Conector | Usa | Para qué |
|---|---|---|
| HUB12 #1 | R = D0, G = D4 | P10 de un color o bicolor |
| HUB12 #2 | R = D1, G = D5 | P10 de un color o bicolor |
| HUB12 #3 | R = D2 | P10 de un color |
| HUB12 #4 | R = D3 | P10 de un color |
| HUB75 | R1 G1 B1 R2 G2 B2 = D0–D5, A–E | módulos a color (P4, P5, P10 RGB), escaneo hasta 1/32 |

- Los 4 HUB12 pueden ser **4 cadenas de un mismo letrero** (más módulos con buen refresco)
  o **4 letreros distintos** con contenido independiente, por ejemplo uno por piso con una sola tarjeta.
- HUB12 y HUB75 comparten líneas: se usa uno u otro según la configuración (no los dos a la vez).
- **HUB75 va desde la Rev A**: módulos RGB de cualquier paso (P2.5, P3, P4, P5, P6, P8, P10) con
  escaneo 1/8, 1/16 y 1/32 (línea E para los de 64 filas), color con profundidad configurable
  (más bits = mejor color, menos refresco) y corrección gamma. Aguanta módulos con chips FM6126A/ICN2038S,
  que necesitan una secuencia de arranque (el firmware la trae como opción del perfil).
- Más módulos a color de lo que da una sola tarjeta: varias tarjetas se sincronizan por red y cada una
  muestra su parte del lienzo (fase 5).
- Buffers 74HCT245 a 5 V (entran 3.3 V, salen 5 V). Las líneas de control se reparten con un
  buffer por cada 2 puertos para no colgar 5 cables planos de una sola salida. Resistencias de 33 Ω
  en serie en cada salida, pull-down en OE (letrero apagado mientras arranca).
- Capacidad estimada con HUB12 de un color, reloj 8 MHz, refresco 200 Hz: unos 75 P10 por cadena,
  así que ~300 P10 con 4 cadenas. En la práctica el límite es la fuente de 5 V. A color (HUB75)
  depende de la profundidad de color: una docena de módulos 64×32 con buen color.

### 1.3 Funciones extra (valor alto, costo bajo)

| Función | Pieza | Qué aporta |
|---|---|---|
| Ethernet | W5500 (igual que la de entrada) | conexión fija en estacionamientos con cable; WiFi de respaldo |
| RS485 | MAX3485 + SM712 | cableados largos existentes; **Modbus RTU** para que un PLC u otro sistema escriba el número |
| 2 entradas optoaisladas | PC817 + PCA9555 | **modo autónomo**: cuenta entradas y salidas desde lazos o botones, funciona sin servidor ni red |
| Brillo automático | fotorresistencia + ADC | se lee de día y no deslumbra de noche; ahorra energía |
| Temperatura | DS18B20 (cable) + la del DS3231 (tarjeta) | alarma y baja el brillo si el gabinete se calienta |
| Ventilador | MOSFET + PCA9555 | se enciende solo por temperatura |
| Relé | relé 5 V 10 A | horario de apagado (cortar los 220 V de las fuentes de noche) y reinicio remoto |
| Monitor de la fuente de los módulos | divisor + ADC | mide sus 5 V: avisa si se cae o se queda corta (módulos tenues) |
| Reloj | DS3231 | horarios y reloj en pantalla aunque no haya red ni NTP |
| Botón | GPIO0 (BOOT) | sostenido: patrón de prueba; muy largo: portal de configuración |
| Protecciones | PTC, MOSFET anti-inversión, TVS SMBJ36A, SM712, optos | lo mismo que se usa en la tarjeta de entrada |

Se descartan por costo o poco valor: PoE (no alimenta los módulos), microSD (16 MB de flash
alcanzan para fuentes, imágenes y mensajes), pantalla local.
**Alimentación (decidido 11 nov 2026): fuente externa exclusiva para la tarjeta.**
- Entrada de **9 a 36 V** (adaptador de 12 V o 24 V de 1 A, o la fuente de 24 V de un gabinete) con
  convertidor buck a 5 V en la tarjeta (LM2596HV o MP1584, como la tarjeta de entrada). Consumo de la
  tarjeta: ~0.3–0.5 A a 5 V. Conector: bornera y jack de barril 5.5×2.1 en paralelo.
- Así la tarjeta no se reinicia cuando los módulos jalan corriente de golpe, y sigue encendida
  (reportando y con el relé disponible) aunque se apague o falle la fuente de los módulos.
- La fuente de los módulos **solo se mide** por una bornera de "medición" (divisor al ADC).
- **Tierra común obligatoria**: el GND de la tarjeta y el de la fuente de los módulos se unen
  (por los GND del cable HUB y además con un cable de tierra a la bornera), o las señales no tienen referencia.

### 1.4 Pines propuestos (DevKitC-1 N16R8)

| Función | GPIO |
|---|---|
| D0–D5 | 4, 5, 6, 7, 15, 16 |
| CLK, LAT, OE | 17, 18, 8 |
| A, B, C, D, E | 9, 10, 11, 12, 13 |
| W5500 SCK, MOSI, MISO, CS | 14, 21, 47, 38 (reset por el PCA9555) |
| RS485 TX, RX, DE | 39, 40, 46 (10 kΩ a GND: arranca recibiendo) |
| I2C SDA, SCL (PCA9555, DS3231) | 41, 42 |
| ADC 5 V de los módulos, ADC luz | 1, 2 |
| 1-Wire DS18B20 | 3 |
| Botón / LED RGB | 0 / 48 |
| Libres para depurar | 43, 44 (UART0), USB 19/20 |

Se evitan 35–37 (PSRAM octal) y 45 (strap de voltaje de la flash).

---

## 2. Firmware

### 2.1 Capas

```
 Editor web (en la tarjeta) · Editor central (openipark.com) · API MQTT / HTTP / Modbus
                                     │
                      Programa (JSON en LittleFS) + variables
                                     │
            Motor de reproducción: páginas → zonas → elementos → efectos
                                     │
               Lienzo (1 bit o RGB) con fuentes UTF-8, imágenes, figuras
                                     │
           Mapeo físico: tamaño, escaneo, orden de bits, cadenas, giro
                                     │
                    Driver LCD_CAM + DMA (HUB12 / HUB75) · brillo por OE
```

### 2.2 Configuración de los módulos (1..N)

Todo desde la página web, sin compilar:
- **Tipo de módulo**: tamaño (32×16, 64×32…), escaneo (1/2, 1/4, 1/8, 1/16, 1/32), colores,
  polaridad de datos y de OE, tabla de orden de bits. Con perfiles ya hechos ("P10 rojo HUB12 1/4", etc.).
- **Geometría**: módulos por cadena, cadenas por puerto, filas × columnas, recorrido en "S",
  giro de cada módulo, y si los puertos forman un solo letrero o letreros separados.
- **Asistente de prueba**: enciende cada módulo con su número y líneas de guía para ajustar
  orden y polaridad en 2 minutos. Muestra el refresco que se logra y avisa si es bajo.

### 2.3 Diseño de mensajes (lo que permite "cualquier cosa")

Modelo parecido al de HD2018, pero en JSON y editable desde el navegador:

- **Programa** → lista de **páginas**. Cada página tiene duración, horario (días/horas),
  condición (`libres == 0`) y prioridad (un mensaje de emergencia interrumpe todo).
- **Página** → **zonas** (rectángulos que se pueden encimar, con borde opcional).
- **Zona** → **elementos**:
  - texto fijo, multilínea o desplazable; alineación, fuente, color, contorno
  - **variables** en el texto: `LIBRES: {libres}`, `{libres.piso2}`, `{hora}`, `{fecha}`, `{temp}`,
    con formato (`{libres:3}`) y reglas (`{libres<5 ? "POCOS" : libres}`, color por condición)
  - reloj y fecha (digital), cuenta regresiva y contador
  - imágenes (BMP/PNG/GIF animado), iconos (flecha, auto, ♿, P)
  - figuras y barra de ocupación
  - código QR (versión 1 = 21×21, cabe en 32 px de alto)
- **Efectos** de entrada y salida: aparecer, desplazar (4 sentidos), persiana, cortina, máquina
  de escribir, parpadeo, desvanecer (a color), con velocidad configurable.
- **Fuentes**: incluidas de pixel (5×7, 6×12, 8×16, 16×32) con acentos y ñ. Cualquier TTF de la PC
  se convierte **en el navegador** a la altura deseada y se sube a la tarjeta.
- **Vista previa exacta**: la tarjeta manda su imagen real al navegador por websocket
  (64 bytes por P10), así la página muestra lo mismo que el letrero, en vivo.
- **Entrada estándar opcional**: mensajes en formato **MULTI de NTCIP 1203**
  (`[jl3][fo2]LIBRES[nl]{libres}`), para quien venga del mundo de letreros viales.

### 2.4 De dónde salen las variables (genérico; OpeniPark es un perfil más)

Cada variable tiene nombre, tipo (número, texto, fecha), valor por omisión y **caducidad**
(si no llega dato en X segundos, muestra "--" o cambia de página), y viene de una fuente:

- **MQTT, cualquier broker**: servidor, usuario, TLS y tópico configurables; el valor puede ser
  el mensaje completo o un campo del JSON (`$.libres`). Prefijo de tópicos configurable
  (`{prefijo}/set`, `…/var/{nombre}`, `…/config` retenido, `…/estado` retenido + LWT).
  - Perfil **OpeniPark**: prefijo `parkit/{id}/letrero/{equipo}`, igual que las barreras.
  - Perfil **Home Assistant**: autodescubrimiento MQTT (el letrero aparece solo en HA).
- **HTTP cliente**: consulta cualquier URL cada N segundos y toma campos del JSON, o el texto plano.
- **HTTP servidor (API REST)**: `POST /api/var/libres 23`, `POST /api/mensaje`, documentada para
  que cualquier sistema (PHP, Python, Node-RED, un script) escriba en el letrero.
- **Modbus RTU** por RS485, en dos modos: **esclavo** (un PLC escribe registros) y **maestro**
  (la tarjeta lee registros de un PLC o un medidor). También Modbus TCP por Ethernet/WiFi.
- **Protocolo serie de texto simple** por RS485 o TTL (`VAR libres=23`), para equipos viejos o
  microcontroladores sin red.
- **Entradas locales**: contador entrada/salida con capacidad configurable (modo autónomo),
  pulsadores (siguiente turno, iniciar cronómetro), o selección de página.
- **Sensores de la propia tarjeta**: temperatura, luz, voltaje, hora.
- **Fórmulas** entre variables: `libres = capacidad - ocupados`, suma de pisos, promedios.

### 2.5 Administración

OTA (web y MQTT), respaldo/restauración de la configuración en un archivo, registro de eventos,
usuario y contraseña en la página, watchdog, y alarmas a OpeniPark (fuente caída, temperatura, sin red).

---

## 3. Costo aproximado (por confirmar con proveedor)

| Bloque | MXN aprox. |
|---|---|
| DevKit ESP32-S3 N16R8 | 150–200 |
| W5500 + RJ45 | 70–100 |
| 74HCT245 ×3, MAX3485, SM712, PCA9555, DS3231, optos, relé, MOSFETs, pasivos | 120–180 |
| PCB 2 capas (lote de 10) y conectores IDC | 60–100 |
| **Total por tarjeta** | **~400–580** |

Referencia: una tarjeta Huidu de un color con WiFi cuesta del mismo orden, pero no se integra
con OpeniPark ni trae Ethernet, RS485, sensores ni modo autónomo.

---

## 4. Fases propuestas

1. **Prototipo de banco**: la ESP32-S3 de repuesto + un 74HCT245 en placa perforada + tus 10 P10.
   Driver LCD_CAM (HUB12 y HUB75 con el mismo código), patrón de prueba, confirmar pinout,
   polaridad y orden de bits. Para probar HUB75 hace falta al menos un módulo RGB (P4/P5 64×32, barato).
2. **Motor de mensajes + editor web** (páginas, zonas, texto, variables, vista previa) y API REST/MQTT.
3. **Esquemático y PCB Rev A** con HUB12 ×4 + HUB75 (estilo A3 con bloques, como las demás tarjetas).
4. **Perfiles de aplicación**: OpeniPark (lugares libres; cambios en el servidor solo con permiso),
   turnos, andon/Modbus, Home Assistant.
5. MULTI (NTCIP), Modbus TCP, varias tarjetas sincronizadas, editor central de flota.

## 5. Software y licencia

- **Firmware abierto** (decidido 11 nov 2026): licencia **GPL-3.0**, igual que el ESP3D de las impresoras.
  Cualquiera lo usa y mejora; quien lo modifique y lo distribuya debe publicar sus cambios.
  El negocio es la tarjeta armada, la instalación y el soporte.
- Repositorio: [itelmex/openledsign](https://github.com/itelmex/openledsign), con:
  firmware, editor web, API documentada, ejemplos de integración (curl, Python, PHP, Node-RED),
  binarios para grabar en línea y procedimiento de programación, como en esp3d-sunlu-s8.
- Librerías abiertas que se usen (p. ej. ESP32-HUB75-MatrixPanel-DMA, licencia MIT; fuentes de pixel)
  se respetan y se les da crédito en el README.
- Hardware: esquemático y PCB también se pueden publicar (por ejemplo CERN-OHL-S) — decisión aparte.

## 6. Decisiones pendientes

- ~~¿HUB75 desde la Rev A?~~ **Sí** (11 nov 2026).
- ~~¿Solo estacionamientos?~~ **No: propósito general** (11 nov 2026).
- ~~¿Alimentación?~~ **Fuente externa exclusiva para la tarjeta, 9–36 V** (11 nov 2026).
- ~~¿Firmware abierto?~~ **Sí, GPL-3.0** (11 nov 2026).
- Nombre: **OpenLed**, si está libre. Revisión rápida (11 nov 2026): no aparece un producto ni marca
  de controladores de letreros con ese nombre, pero hay repos chicos en GitHub llamados "OpenLED"
  (controlador de tiras LED para casa, placas para drones), el dominio openled.io lo usa la empresa de
  iluminación FTSLED, y openled.com está registrado. **Falta buscar en el IMPI (MARCia, clase 9)** antes de usarlo.
  Alternativa en la línea de OpeniPark: **OpeniLed** (sin repos en GitHub, openiled.com sin registrar).
- ¿Cuántos relés? Aún no se sabe; se propone dejar 1 en la Rev A y **2 huellas** (el segundo se arma si hace falta).
- ¿Cuántas entradas optoaisladas (2 propuestas)?
- Para el perfil OpeniPark: ¿el número de lugares libres sale de MQTT o de parkit_alfa, y va por piso o zona?
