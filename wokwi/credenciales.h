/* Credenciales para SIMULAR en wokwi.com (no usar en el ESP32 real).
 * Usa el broker PÚBLICO de HiveMQ: no hace falta usuario ni contraseña,
 * pero cualquiera que conozca el prefijo puede leer los mensajes.
 * Cambie "juanjo" por algo propio para no cruzarse con otros usuarios. */
#ifndef CREDENCIALES_H
#define CREDENCIALES_H

#define SIMULACION_WOKWI            /* activa planta_wokwi.h */

#define WIFI_SSID       "Wokwi-GUEST"
#define WIFI_PASSWORD   ""
#define WIFI_CANAL      6

#define MQTT_SERVER     "broker.hivemq.com"
#define MQTT_PORT       8883
#define MQTT_USER       ""
#define MQTT_PASSWORD   ""
#define MQTT_PREFIJO    "unimag/v20-juanjo"

#endif
