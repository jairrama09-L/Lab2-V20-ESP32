/* =============================================================================
 *  credenciales.h
 *  -----------------------------------------------------------------------------
 *  PLANTILLA PUBLICA. Este archivo SI se sube al repositorio.
 *
 *  Uso:
 *    1. Copie este archivo como "credenciales.h" dentro de la misma carpeta
 *       del sketch.
 *    2. Escriba en el nuevo archivo sus datos reales de Wi-Fi y del broker.
 *    3. Verifique que el archivo .gitignore contenga la linea "credenciales.h"
 *       para que NUNCA se publique en GitHub.
 *
 *  Motivo: una contrasena escrita dentro del .ino queda expuesta de forma
 *  permanente en el historial del repositorio, aunque despues se borre del
 *  archivo. Si eso llega a ocurrir, no basta con borrarla: hay que cambiarla
 *  en el broker.
 * =============================================================================
 */

#ifndef CREDENCIALES_H
#define CREDENCIALES_H

/* ---------------------------- Red Wi-Fi ---------------------------------- */
#define WIFI_SSID       "realme 9"
#define WIFI_PASSWORD   "andres123"

/* ---------------------------- Broker MQTT -------------------------------- */
#define MQTT_SERVER     "4f74e46887674798998beba9cfd4a9c7.s1.eu.hivemq.cloud"
#define MQTT_PORT       8883
#define MQTT_USER       "jair_esp32"
#define MQTT_PASSWORD   "jalo0310"

/* ---------------------------- Prefijo de topicos -------------------------- */
/* Todos los topicos cuelgan de este prefijo. Cambielo si varios equipos
 * comparten el mismo broker, para no interferir entre grupos.               */
#define MQTT_PREFIJO    "jair/v20"

/* ---------------------------- Certificado raiz TLS ------------------------
 *  Recomendado para produccion. Si se define MQTT_CA_CERT, el ESP32 valida
 *  el certificado del broker; si no se define, el firmware usa setInsecure()
 *  (cifra, pero NO autentica al servidor) y lo advierte por el monitor serial.
 *
 *  Para HiveMQ Cloud se usa el certificado raiz de Let's Encrypt (ISRG Root X1),
 *  que se descarga del sitio de la autoridad certificadora y se pega aqui
 *  completo, incluidas las lineas BEGIN/END.
 *
 *  #define MQTT_CA_CERT R"EOF(
 *  -----BEGIN CERTIFICATE-----
 *  ...
 *  -----END CERTIFICATE-----
 *  )EOF"
 * -------------------------------------------------------------------------- */

#endif  /* CREDENCIALES_H */
