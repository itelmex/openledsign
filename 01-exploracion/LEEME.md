# Tarjeta Letrero OpeniPark (TL-S3) — exploración

Luis (@itelmex) · 11 nov 2026 · Estado: **exploración** (nada fabricado ni probado)

Idea: un hardware estándar de OpeniPark para letreros de LED, como la tarjeta de entrada
(tarjeta-openipark-s3): misma DevKit, mismas piezas, mismas protecciones, y un firmware que
se configura para **1 hasta N módulos** y permite **cualquier diseño de mensaje**.
Valor frente a una tarjeta Huidu/Onbon: se integra con OpeniPark (lugares libres en vivo),
se maneja desde un navegador sin instalar nada, Ethernet + WiFi, monitoreo remoto, y es nuestro.

---

## 1. Hardware

### 1.1 Bloques

```
                 ┌──────────────────────────── TL-S3 ────────────────────────────┐
 5 V (fuente ──► │ PTC/fusible → MOSFET anti-inversión → TVS → 1000 µF → DevKit  │
 de los módulos) │       └─ divisor → ADC: mide los 5 V (detecta fuente caída)   │
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
| Monitor de 5 V | divisor + ADC | avisa si la fuente se cae o se queda corta (los módulos se ven tenues) |
| Reloj | DS3231 | horarios y reloj en pantalla aunque no haya red ni NTP |
| Botón | GPIO0 (BOOT) | sostenido: patrón de prueba; muy largo: portal de configuración |
| Protecciones | PTC, MOSFET anti-inversión, TVS SMBJ5.0A, SM712, optos | lo mismo que se usa en la tarjeta de entrada |

Se descartan por costo o poco valor: PoE (no alimenta los módulos), microSD (16 MB de flash
alcanzan para fuentes, imágenes y mensajes), pantalla local.
Alimentación de 9–36 V: huella opcional para un buck (MP1584) si la tarjeta va lejos de la fuente de 5 V.

### 1.4 Pines propuestos (DevKitC-1 N16R8)

| Función | GPIO |
|---|---|
| D0–D5 | 4, 5, 6, 7, 15, 16 |
| CLK, LAT, OE | 17, 18, 8 |
| A, B, C, D, E | 9, 10, 11, 12, 13 |
| W5500 SCK, MOSI, MISO, CS | 14, 21, 47, 38 (reset por el PCA9555) |
| RS485 TX, RX, DE | 39, 40, 46 (10 kΩ a GND: arranca recibiendo) |
| I2C SDA, SCL (PCA9555, DS3231) | 41, 42 |
| ADC 5 V, ADC luz | 1, 2 |
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

### 2.4 De dónde salen las variables

- **MQTT** (EMQX de OpeniPark): `parkit/{id}/letrero/{equipo}/set`, `…/var/{nombre}`,
  `…/config` (retenido), `…/estado` (retenido + LWT), igual que las barreras.
- **HTTP**: la tarjeta consulta un JSON (por ejemplo de parkit_alfa) o recibe un POST.
- **Modbus RTU** por RS485: registros = variables.
- **Entradas locales**: contador entrada/salida con capacidad configurable (modo autónomo).
- **Sensores de la propia tarjeta**: temperatura, luz, voltaje.

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
   Driver LCD_CAM, patrón de prueba, confirmar pinout, polaridad y orden de bits.
2. **Motor de mensajes + editor web** (páginas, zonas, texto, variables, vista previa).
3. **Integración OpeniPark**: MQTT/HTTP de lugares libres (cambios en el servidor solo con permiso).
4. **Esquemático y PCB Rev A** (estilo A3 con bloques, como las demás tarjetas).
5. HUB75 a color, Modbus, MULTI, editor central en openipark.com.

## 5. Decisiones pendientes

- ¿HUB75 (color) desde la Rev A, o solo HUB12?
- ¿Entrada solo de 5 V, o también la huella del buck de 9–36 V?
- ¿Cuántas entradas optoaisladas y relés (2 + 1 propuestos)?
- ¿De dónde sale el número de lugares libres (MQTT o parkit_alfa) y si va por piso o zona?
