# Control IoT del SINAMICS V20 con ESP32 (extensión del Lab 2)

Desde la app del celular se manda el V20: marcha, paro, sentido, consigna de 0 a 60 Hz, reset de falla y emergencia. La app muestra la corriente de una fase medida con un ACS712 y el estado real del variador. El ESP32 ejecuta las protecciones aunque la app no esté conectada.

```
App (celular) ⇄ HiveMQ Cloud (MQTT/TLS) ⇄ ESP32 ─┬─ PWM → 6N137 → acondicionador → AI1 (borne 89)
                                                 ├─ módulo de relés ×3 → DI1/DI2/DI3 (bornes 95/96/97)
                                                 ├─ DO1 en marcha, directo a GPIO35 (bornes 102/103)
                                                 ├─ relé DO2 falla (bornes 105/106)
                                                 └─ ACS712 en la fase U (borne 83 → borne 1)
```

| Carpeta | Contenido |
|---|---|
| `firmware/v20_iot_esp32/` | Firmware v3.1. Copie `credenciales_ejemplo.h` como `credenciales.h` y complételo. |
| `app/index.html` | App web sin dependencias (MQTT sobre WebSocket). Para GitHub Pages, cópiela a `docs/index.html`. |
| `docs/Guia_Conexiones_V20_IoT.pdf` | Cableado pin a pin, parámetros del V20, pruebas y protecciones. |
| `sim/` | Simulación: firmware real + modelo del V20/motor + broker MQTT + app manejada con Playwright. |
| `sim/resultados/Reporte_Simulacion_V20_IoT.pdf` | Resultado: 30 de 30 pruebas pasan. |

## Parámetros del V20 (además de la puesta en marcha rápida y el escalado de AI1)
P0700 = 2 · P1000 = 2 · P0701 = 1 · P0702 = 12 · P0703 = 9 · P0731 = 52.2 · P0732 = 52.3

## Compilar el firmware
Arduino IDE, placa "ESP32 Dev Module", librería **PubSubClient**. Compila con el núcleo esp32 2.x o 3.x.

## Consola serie (115 200 baudios, "Nueva línea")
`0..60` consigna · `marcha` · `paro` · `emerg` · `reset` · `adelante` · `atras` · `p` perfil · `s` parar perfil · `cal` · `i` estado · `d` diagnóstico · `rampa=5` · `in=3.2` · `fmin=0` · `fmax=60` · `vigilancia=1`
