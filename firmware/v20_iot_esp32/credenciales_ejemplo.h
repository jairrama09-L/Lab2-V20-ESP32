/* Copie este archivo como "credenciales.h" en la misma carpeta y complete sus datos.
 * credenciales.h está en .gitignore: NO lo suba al repositorio. */
#ifndef CREDENCIALES_H
#define CREDENCIALES_H

#define WIFI_SSID       "nombre_de_la_red"
#define WIFI_PASSWORD   "clave_de_la_red"

#define MQTT_SERVER     "xxxxxxxxxxxxxxxx.s1.eu.hivemq.cloud"   /* el mismo del Lab 1 */
#define MQTT_PORT       8883
#define MQTT_USER       "usuario_esp32"
#define MQTT_PASSWORD   "clave_esp32"

/* Prefijo de tópicos. Debe ser EL MISMO que se escribe en la app. */
#define MQTT_PREFIJO    "jair/v20"

#endif
