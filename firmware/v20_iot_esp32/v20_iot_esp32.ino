/* =============================================================================
 *  CONTROL IoT DEL SINAMICS V20 CON ESP32
 *  Consigna analógica aislada (PWM → AI1) + mando por entradas digitales +
 *  retorno de estado + medición de corriente de fase + supervisión MQTT
 * -----------------------------------------------------------------------------
 *  Universidad del Magdalena · Ingeniería Electrónica · Electrónica de Potencia
 *  Laboratorio N.º 2 (extensión IoT) · Docente: Ing. Jordan D. Guillot Fula
 *  Versión 3.1 · Plataforma: ESP32 DevKit V1, núcleo Arduino-ESP32 2.0.x o 3.x
 *  Librería adicional: PubSubClient (Nick O'Leary)
 * -----------------------------------------------------------------------------
 *  QUÉ HACE
 *   1. Genera la consigna 0–10 V de AI1 con PWM de 20 kHz y 10 bits (igual que
 *      la Guía N.º 2): GPIO25 → 6N137 → 74HC14 → RC → LM358 → AI1.
 *   2. Manda marcha/paro, sentido y reconocimiento de falla por las entradas
 *      digitales DI1, DI2 y DI3 del V20, con un módulo de relés (contacto seco).
 *   3. Lee del V20 "en marcha" (DO1, transistor) y "falla activa" (DO2, relé).
 *   4. Mide la corriente RMS de una fase del motor con un ACS712.
 *   5. Publica todo por MQTT (HiveMQ Cloud, TLS) y recibe órdenes de la app.
 *   6. Protege: pérdida de corriente de fase, sobrecorriente, I²t, falla del V20,
 *      V20 que no responde, sensor desconectado, pérdida de comunicación y
 *      reinicio del ESP32. Toda falla deja DI1 abierto y la consigna en 0 V.
 * -----------------------------------------------------------------------------
 *  PARÁMETROS DEL V20 PARA ESTE MODO (además de la puesta en marcha rápida)
 *   P0700 = 2     Fuente de órdenes: bornes (DI)
 *   P1000 = 2     Consigna de frecuencia: entrada analógica AI1
 *   P0701 = 1     DI1: ON/OFF1 (marcha con rampa P1120, paro con rampa P1121)
 *   P0702 = 12    DI2: inversión de sentido
 *   P0703 = 9     DI3: reconocimiento de falla
 *   P0731 = 52.2  DO1: convertidor en marcha
 *   P0732 = 52.3  DO2: falla activa
 *   P0756..P0760, P2000: escalado de AI1 como en la Guía N.º 2 (P0759 = r0752)
 * -----------------------------------------------------------------------------
 *  MAPA DE PINES (ver guía de conexiones)
 *   GPIO25 → R 220 Ω → 6N137 (consigna PWM)
 *   GPIO26 → IN1 módulo de relés → contacto COM–NO: borne 100 (24 V) → DI1 (95)  MARCHA
 *   GPIO27 → IN2 módulo de relés → contacto COM–NO: borne 100 (24 V) → DI2 (96)  INVERSIÓN
 *   GPIO32 → IN3 módulo de relés → contacto COM–NO: borne 100 (24 V) → DI3 (97)  RECONOCER
 *            Módulo de relés electromecánicos de 5 V (contacto seco). Los módulos
 *            comunes se activan en BAJO: ver RELE_ACTIVO_BAJO. Pull-up de 10 kΩ a
 *            3,3 V en cada IN para que ningún relé cierre durante el reset.
 *            NO usar el módulo de relés de ESTADO SÓLIDO del Lab 1 (G3MB-202P):
 *            su salida es un triac de CA y no conmuta bien los 24 V CC del V20.
 *   GPIO35 ← DO1+ (borne 102); DO1− (borne 103) a GND del ESP32   EN MARCHA, activo en BAJO
 *            DO1 es un transistor aislado (500 V) y libre de potencial: actúa como
 *            interruptor sobre GPIO35. GPIO35 no tiene pull-up: 10 kΩ a 3,3 V obligatoria.
 *   GPIO33 ← contacto NO del relé DO2 (borne 105; común 106 a GND)  FALLA, activo en BAJO
 *   GPIO34 ← ACS712: OUT → 10 kΩ → GPIO34 → 20 kΩ ∥ 22 nF → GND
 *   GPIO2  → LED de estado
 *  Con el ESP32 apagado o en reset los relés quedan abiertos (pull-ups) y el
 *  LED del 6N137 apagado: DI1 = 0 (paro) y AI1 = 0 V. Falla hacia el lado seguro.
 * =============================================================================
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <math.h>
#include <esp_system.h>
#include "credenciales.h"

/* ============================ TÓPICOS MQTT ================================ */
#define TOPIC_CMD         MQTT_PREFIJO "/cmd"         /* app → ESP32: órdenes        */
#define TOPIC_CONSIGNA    MQTT_PREFIJO "/consigna"    /* app → ESP32: Hz              */
#define TOPIC_CONFIG      MQTT_PREFIJO "/config"      /* app → ESP32: clave=valor     */
#define TOPIC_ESTADO      MQTT_PREFIJO "/estado"      /* ESP32 → app (retenido)       */
#define TOPIC_ALARMA      MQTT_PREFIJO "/alarma"      /* ESP32 → app: causa de falla (retenido) */
#define TOPIC_AVISO       MQTT_PREFIJO "/aviso"       /* ESP32 → app: órdenes rechazadas, info  */
#define TOPIC_TELEMETRIA  MQTT_PREFIJO "/telemetria"  /* ESP32 → app: JSON cada 1 s   */
#define TOPIC_ONLINE      MQTT_PREFIJO "/online"      /* ESP32 → app: testamento      */

/* ============================ PINES ======================================= */
const uint8_t PIN_PWM    = 25;
const uint8_t PIN_DI1    = 26;
const uint8_t PIN_DI2    = 27;
const uint8_t PIN_DI3    = 32;
const uint8_t PIN_DO1    = 35;
const uint8_t PIN_DO2    = 33;
const uint8_t PIN_SENSOR = 34;
const uint8_t PIN_LED    = 2;

/* Módulo de relés: true si el relé cierra con nivel BAJO en su entrada (lo más común). */
#ifndef RELE_ACTIVO_BAJO
#define RELE_ACTIVO_BAJO 1
#endif
const uint8_t RELE_ON  = RELE_ACTIVO_BAJO ? LOW : HIGH;
const uint8_t RELE_OFF = RELE_ACTIVO_BAJO ? HIGH : LOW;

/* ============================ CONSIGNA PWM ================================ */
const int      CANAL_PWM = 0;          /* solo núcleo 2.x */
const uint32_t F_PWM     = 20000;
const uint8_t  BITS_PWM  = 10;
const int      D_MAX     = (1 << BITS_PWM) - 1;
const float    F_REF     = 60.0f;      /* Hz con D = 100 % (P2000) */
const float    V_FS      = 10.0f;

/* ============================ TEMPORIZACIÓN =============================== */
const unsigned long INTERVALO_TELEMETRIA_MS = 1000;
const unsigned long INTERVALO_MQTT_MS       = 5000;
const unsigned long INTERVALO_WIFI_MS       = 10000;
const unsigned long TIMEOUT_COMUNICACION_MS = 10000;
const unsigned long VENTANA_RETENIDOS_MS    = 1500;  /* retenidos llegan < 1 s tras suscribir */
const unsigned long REBOTE_ENTRADAS_MS      = 50;
const unsigned long PULSO_RECONOCER_MS      = 300;
const unsigned long ESPERA_RECONOCER_MS     = 2000;
const unsigned long TIEMPO_RESPUESTA_V20_MS = 2000;  /* DI1 activo sin DO1 */
const unsigned long T_ESCALON_MS            = 20000;
const float PASOS_PERFIL[] = {0, 15, 30, 45, 60, 30, 0};
const int   N_PASOS = sizeof(PASOS_PERFIL) / sizeof(PASOS_PERFIL[0]);

/* ============================ MEDICIÓN DE CORRIENTE ======================= */
const unsigned long PERIODO_MUESTREO_US = 500;      /* 2 kHz */
const uint8_t       SOBREMUESTREO       = 4;
/* ACS712: 0,185 V/A (5 A) · 0,100 V/A (20 A) · 0,066 V/A (30 A).
 * Para un motor de 1 HP se recomienda la versión de 5 A: 2,8 veces más señal. */
const float SENSIBILIDAD_ACS712 = 0.066;
const float RELACION_DIVISOR    = 20.0 / (10.0 + 20.0);
const float UMBRAL_RUIDO_A      = 0.15;
const float V_MEDIA_MIN = 2.20, V_MEDIA_MAX = 2.80;
const uint8_t VENTANAS_FALLA_SENSOR = 2;
const int MUESTRAS_CALIBRACION = 1000;

/* ============================ PROTECCIONES ================================ */
float corrienteNominalA = 0.0;            /* 0 = I²t y sobrecorriente inhibidas */
const float THETA_DISPARO = 1.20, THETA_ADVERTENCIA = 0.90, THETA_REARME = 0.60;
#ifndef TAU_TERMICA_S
#define TAU_TERMICA_S 300
#endif
const float         FACTOR_SOBRECORRIENTE  = 2.5;
const unsigned long TIEMPO_SOBRECORRIENTE_MS = 500;
bool                vigilarPerdida          = true;
const float         UMBRAL_PERDIDA_A        = 0.35;
const float         FRACCION_PERDIDA        = 0.15;
const float         F_MIN_VIGILANCIA_HZ     = 5.0;
const unsigned long INHIBICION_PERDIDA_MS   = 3000;
const unsigned long TIEMPO_PERDIDA_MS       = 2000;
const bool          BLOQUEO_TRAS_REINICIO   = true;

/* ============================ ESTADO ====================================== */
enum Estado { DETENIDO, MARCHA, FALLO };
Estado estado = DETENIDO;

float consignaHz      = 0.0f;   /* pedida por la app o la consola        */
float consignaAplicada = 0.0f;  /* la que sale por AI1 (tras la rampa)    */
float rampaEspS = 0.0f;         /* rampa propia del ESP32; 0 = la del V20 */
float fMinHz = 0.0f, fMaxHz = 60.0f;
int   dutyActual = -1;
bool  sentidoInverso = false;
bool  marchaRemota = false;
bool  perfilActivo = false;
int   pasoPerfil = 0;
bool  pulsoReconocer = false;
bool  esperandoReconocer = false;

/* Entradas del V20 (ya filtradas) */
bool v20Marcha = false, v20Falla = false;
bool lecturaDO1 = false, lecturaDO2 = false;
unsigned long cambioDO1 = 0, cambioDO2 = 0;

/* Marcas de tiempo */
unsigned long instanteEstado = 0, instanteSuscripcion = 0, instantePerdidaCom = 0;
unsigned long ultimaTelemetria = 0, ultimoIntentoMQTT = 0, ultimoIntentoWiFi = 0;
unsigned long instanteLed = 0, ultimaMuestraUs = 0, inicioVentana = 0;
unsigned long instanteTermica = 0, instanteRampa = 0, instantePaso = 0;
unsigned long instantePulso = 0, instanteSinMarcha = 0, instantePerdida = 0;
unsigned long instanteSobrecorriente = 0;
bool temporizandoSinMarcha = false, temporizandoPerdida = false;
bool temporizandoSobrecorriente = false, advertenciaTermica = false;
bool estadoLed = false;

/* Medición */
enum Calibracion { CAL_INACTIVA, CAL_PENDIENTE, CAL_MUESTREANDO };
Calibracion calibracion = CAL_INACTIVA;
float corrienteRms = 0, voltajeCero = 2.5, voltajeMedio = 0, ruidoA = 0, theta = 0;
bool sensorOK = true, calibracionValida = false;
uint8_t ventanasMalas = 0;
double sumaV = 0, sumaV2 = 0, sumaCalV = 0, sumaCalV2 = 0;
unsigned long nMuestras = 0, nCal = 0, muestrasPorSegundo = 0;

char ultimaAlarma[40] = "SIN_ALARMA";
WiFiClientSecure clienteSeguro;
PubSubClient mqtt(clienteSeguro);

/* ========================================================================== */
/*  UTILIDADES                                                                */
/* ========================================================================== */
const char* nombreEstado(Estado e) {
  switch (e) { case DETENIDO: return "DETENIDO"; case MARCHA: return "MARCHA"; default: return "FALLO"; }
}

void publicarAlarma(const char* a) {
  snprintf(ultimaAlarma, sizeof(ultimaAlarma), "%s", a);
  if (mqtt.connected()) mqtt.publish(TOPIC_ALARMA, a, true);
  Serial.print("ALARMA: "); Serial.println(a);
}

/* Avisos: órdenes rechazadas e información. No reemplazan la causa de la falla. */
void publicarAviso(const char* a) {
  if (mqtt.connected()) mqtt.publish(TOPIC_AVISO, a, false);
  Serial.print("AVISO: "); Serial.println(a);
}

void publicarEstado() {
  if (mqtt.connected()) mqtt.publish(TOPIC_ESTADO, nombreEstado(estado), true);
}

bool enlaceOK() { return WiFi.status() == WL_CONNECTED && mqtt.connected(); }

/* ========================================================================== */
/*  SALIDAS: PWM DE CONSIGNA Y ENTRADAS DIGITALES DEL V20                     */
/* ========================================================================== */
void pwmInit() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(PIN_PWM, F_PWM, BITS_PWM);
#else
  ledcSetup(CANAL_PWM, F_PWM, BITS_PWM);
  ledcAttachPin(PIN_PWM, CANAL_PWM);
#endif
}

void pwmWrite(int d) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(PIN_PWM, d);
#else
  ledcWrite(CANAL_PWM, d);
#endif
}

/* Única función que escribe las salidas. En FALLO no hay marcha ni consigna. */
void aplicarSalidas() {
  bool marcha = (estado == MARCHA);
  float f = (estado == FALLO) ? 0.0f : consignaAplicada;
  int d = (int)lroundf(f / F_REF * D_MAX);
  if (d != dutyActual) { dutyActual = d; pwmWrite(d); }
  digitalWrite(PIN_DI1, marcha ? RELE_ON : RELE_OFF);
  digitalWrite(PIN_DI2, sentidoInverso ? RELE_ON : RELE_OFF);
  digitalWrite(PIN_DI3, pulsoReconocer ? RELE_ON : RELE_OFF);
}

float limitar(float f) {
  if (f < 0) f = 0;
  if (f > F_REF) f = F_REF;
  if (f < fMinHz) f = fMinHz;
  if (f > fMaxHz) f = fMaxHz;
  return f;
}

/* Rampa propia (opcional) entre la consigna pedida y la aplicada. */
void actualizarRampa() {
  unsigned long ahora = millis();
  float dt = (ahora - instanteRampa) / 1000.0f;
  instanteRampa = ahora;
  float objetivo = limitar(consignaHz);
  if (rampaEspS <= 0.0f) {
    consignaAplicada = objetivo;
  } else {
    float paso = F_REF / rampaEspS * dt;
    if (fabsf(objetivo - consignaAplicada) <= paso) consignaAplicada = objetivo;
    else consignaAplicada += (objetivo > consignaAplicada) ? paso : -paso;
  }
}

/* ========================================================================== */
/*  MÁQUINA DE ESTADOS                                                        */
/* ========================================================================== */
void mostrarEstado() {
  Serial.printf("ESTADO %s | consigna %.2f Hz (aplicada %.2f, AI1 %.3f V) | %s | DI1=%d DI2=%d | "
                "V20 marcha=%d falla=%d | I=%.2f A | alarma %s\n",
                nombreEstado(estado), consignaHz, consignaAplicada, V_FS * dutyActual / D_MAX,
                sentidoInverso ? "ATRAS" : "ADELANTE", estado == MARCHA, sentidoInverso,
                v20Marcha, v20Falla, corrienteRms, ultimaAlarma);
}

void cambiarEstado(Estado nuevo) {
  estado = nuevo;
  instanteEstado = millis();
  temporizandoSinMarcha = temporizandoPerdida = temporizandoSobrecorriente = false;
  if (nuevo != MARCHA) marchaRemota = false;
  aplicarSalidas();
  mostrarEstado();
  publicarEstado();
}

void activarFallo(const char* motivo) {
  perfilActivo = false;
  cambiarEstado(FALLO);       /* DI1 abierto y AI1 = 0 V antes de informar */
  publicarAlarma(motivo);
}

void iniciarMarcha(bool remota) {
  if (estado == FALLO)              { publicarAviso("MARCHA_RECHAZADA_FALLO"); return; }
  if (estado == MARCHA)             { return; }
  if (v20Falla)                     { publicarAviso("MARCHA_RECHAZADA_FALLA_V20"); return; }
  if (calibracion != CAL_INACTIVA)  { publicarAviso("MARCHA_RECHAZADA_CALIBRANDO"); return; }
  if (!sensorOK)                    { publicarAviso("MARCHA_RECHAZADA_SENSOR"); return; }
  if (corrienteNominalA > 0 && theta > THETA_REARME) { publicarAviso("MARCHA_RECHAZADA_TERMICO"); return; }
  if (remota && !enlaceOK())        { return; }
  marchaRemota = remota;
  advertenciaTermica = false;
  publicarAlarma("SIN_ALARMA");
  cambiarEstado(MARCHA);
}

void detener() {
  perfilActivo = false;
  if (estado == FALLO) { Serial.println("En FALLO: use RESET."); return; }
  if (estado == MARCHA) cambiarEstado(DETENIDO);
}

void cambiarSentido(bool inverso) {
  if (inverso == sentidoInverso) return;
  /* Invertir en marcha regenera energía hacia el bus de CC (sin resistencia de
   * frenado el V20 dispara por sobretensión). Solo con el motor parado. */
  if (estado == MARCHA || v20Marcha) { publicarAviso("SENTIDO_RECHAZADO_EN_MARCHA"); return; }
  sentidoInverso = inverso;
  aplicarSalidas();
  Serial.printf("Sentido: %s\n", inverso ? "ATRAS" : "ADELANTE");
}

void rearmar() {
  if (estado != FALLO)  { Serial.println("RESET: no hay falla activa."); return; }
  if (v20Marcha)        { publicarAviso("RESET_RECHAZADO_MOTOR_GIRANDO"); return; }
  if (corrienteNominalA > 0 && theta > THETA_REARME) { publicarAviso("RESET_RECHAZADO_TERMICO"); return; }
  /* Pulso en DI3: reconoce la falla del V20 (si la hay) antes de rearmar. */
  pulsoReconocer = true;
  esperandoReconocer = true;
  instantePulso = millis();
  aplicarSalidas();
  Serial.println("Reconociendo falla en el V20 (pulso DI3)...");
}

void atenderReconocimiento() {
  if (!esperandoReconocer) return;
  unsigned long t = millis() - instantePulso;
  if (pulsoReconocer && t >= PULSO_RECONOCER_MS) { pulsoReconocer = false; aplicarSalidas(); }
  if (!pulsoReconocer && !v20Falla) {
    esperandoReconocer = false;
    cambiarEstado(DETENIDO);
    publicarAlarma(sensorOK ? "SIN_ALARMA" : "SENSOR_CORRIENTE_FALLA");
    Serial.println("Sistema rearmado.");
  } else if (t >= ESPERA_RECONOCER_MS) {
    esperandoReconocer = false;
    publicarAviso("FALLA_V20_PERSISTE");
  }
}

void atenderPerfil() {
  if (!perfilActivo || millis() - instantePaso < T_ESCALON_MS) return;
  if (++pasoPerfil >= N_PASOS) { perfilActivo = false; Serial.println("Perfil terminado"); return; }
  instantePaso = millis();
  consignaHz = PASOS_PERFIL[pasoPerfil];
  Serial.printf("t=%lu ms | perfil paso %d: %.0f Hz\n", millis(), pasoPerfil + 1, consignaHz);
}

void iniciarPerfil() {
  perfilActivo = true; pasoPerfil = 0; instantePaso = millis();
  consignaHz = PASOS_PERFIL[0];
  Serial.println("Perfil de escalones iniciado");
}

/* ========================================================================== */
/*  ENTRADAS DEL V20                                                          */
/* ========================================================================== */
void leerEntradas() {
  unsigned long ahora = millis();
  bool l1 = (digitalRead(PIN_DO1) == LOW);  /* PC817 conduce = V20 en marcha */
  bool l2 = (digitalRead(PIN_DO2) == LOW);  /* relé cerrado = falla activa   */
  if (l1 != lecturaDO1) { lecturaDO1 = l1; cambioDO1 = ahora; }
  if (l2 != lecturaDO2) { lecturaDO2 = l2; cambioDO2 = ahora; }
  if (ahora - cambioDO1 >= REBOTE_ENTRADAS_MS && v20Marcha != lecturaDO1) {
    v20Marcha = lecturaDO1;
    Serial.printf("V20 %s\n", v20Marcha ? "EN MARCHA" : "PARADO");
  }
  if (ahora - cambioDO2 >= REBOTE_ENTRADAS_MS && v20Falla != lecturaDO2) {
    v20Falla = lecturaDO2;
    Serial.printf("V20 falla %s\n", v20Falla ? "ACTIVA" : "despejada");
    if (v20Falla && estado != FALLO) activarFallo("FALLA_V20");
  }
}

/* DI1 activo y el V20 no confirma marcha: red cortada, P0700 mal configurado,
 * cable de DI1 suelto o V20 apagado. */
void verificarRespuestaV20() {
  if (estado != MARCHA || v20Marcha) { temporizandoSinMarcha = false; return; }
  if (!temporizandoSinMarcha) { temporizandoSinMarcha = true; instanteSinMarcha = millis(); return; }
  if (millis() - instanteSinMarcha >= TIEMPO_RESPUESTA_V20_MS) activarFallo("V20_SIN_MARCHA");
}

/* ========================================================================== */
/*  MEDICIÓN DE CORRIENTE (algoritmo corregido del Lab 1, v2)                 */
/* ========================================================================== */
float leerVoltajeACS() {
  uint32_t s = 0;
  for (uint8_t i = 0; i < SOBREMUESTREO; i++) s += analogReadMilliVolts(PIN_SENSOR);
  return (s / (float)SOBREMUESTREO) / 1000.0f / RELACION_DIVISOR;
}

float umbralRuido() { float u = 3.0f * ruidoA; return u > UMBRAL_RUIDO_A ? u : UMBRAL_RUIDO_A; }

/* Ventana de 5 periodos de la frecuencia aplicada, entre 0,4 y 2 s:
 * a 60 Hz son 24 ciclos; a 5 Hz, 5 ciclos completos. */
unsigned long ventanaMs() {
  float f = consignaAplicada > 1.0f ? consignaAplicada : 1.0f;
  unsigned long w = (unsigned long)(5000.0f / f);
  if (w < 400) w = 400;
  if (w > 2000) w = 2000;
  return w;
}

void evaluarSensor(float media) {
  if (media >= V_MEDIA_MIN && media <= V_MEDIA_MAX) {
    ventanasMalas = 0;
    if (!sensorOK) { sensorOK = true; Serial.println("Sensor recuperado."); if (estado != FALLO) publicarAlarma("SIN_ALARMA"); }
    return;
  }
  if (ventanasMalas < 255) ventanasMalas++;
  if (sensorOK && ventanasMalas >= VENTANAS_FALLA_SENSOR) {
    sensorOK = false;
    Serial.printf("Sensor fuera de rango: media %.3f V\n", media);
    if (estado == MARCHA) activarFallo("FALLO_SENSOR_CORRIENTE");
    else publicarAlarma("SENSOR_CORRIENTE_FALLA");
  }
}

void iniciarCalibracion() {
  if (estado == MARCHA) { publicarAviso("CALIBRACION_RECHAZADA"); return; }
  calibracion = CAL_PENDIENTE;   /* espera a que el V20 confirme motor parado */
  Serial.println("Calibración del ACS712 pendiente (espera motor parado)...");
}

void procesarCalibracion(float v) {
  sumaCalV += v; sumaCalV2 += (double)v * v;
  if (++nCal < (unsigned long)MUESTRAS_CALIBRACION) return;
  double media = sumaCalV / nCal, var = sumaCalV2 / nCal - media * media;
  if (var < 0) var = 0;
  calibracion = CAL_INACTIVA;
  inicioVentana = millis(); sumaV = sumaV2 = 0; nMuestras = 0;
  if (media < V_MEDIA_MIN || media > V_MEDIA_MAX) {
    calibracionValida = false; sensorOK = false; ventanasMalas = VENTANAS_FALLA_SENSOR;
    Serial.printf("Calibración INVÁLIDA: media %.3f V\n", media);
    publicarAviso("ACS712_CAL_INVALIDA");
    return;
  }
  voltajeCero = media; ruidoA = sqrt(var) / SENSIBILIDAD_ACS712;
  calibracionValida = true; sensorOK = true; ventanasMalas = 0;
  Serial.printf("ACS712: cero %.4f V | ruido %.3f A | umbral %.3f A\n", voltajeCero, ruidoA, umbralRuido());
  publicarAviso("ACS712_CALIBRADO");
}

void actualizarCorriente() {
  unsigned long us = micros();
  if (us - ultimaMuestraUs < PERIODO_MUESTREO_US) return;
  ultimaMuestraUs = us;

  if (calibracion == CAL_PENDIENTE) {
    if (v20Marcha) return;
    calibracion = CAL_MUESTREANDO; sumaCalV = sumaCalV2 = 0; nCal = 0; corrienteRms = 0;
  }
  float v = leerVoltajeACS();
  if (calibracion == CAL_MUESTREANDO) { procesarCalibracion(v); return; }

  sumaV += v; sumaV2 += (double)v * v; nMuestras++;
  unsigned long ahora = millis();
  if (ahora - inicioVentana < ventanaMs()) return;
  if (nMuestras >= 10) {
    double media = sumaV / nMuestras, var = sumaV2 / nMuestras - media * media;
    if (var < 0) var = 0;
    voltajeMedio = (float)media;
    evaluarSensor(voltajeMedio);
    if (sensorOK) {
      float im = sqrt(var) / SENSIBILIDAD_ACS712;
      float i2 = im * im - ruidoA * ruidoA;
      float i = i2 > 0 ? sqrt(i2) : 0;
      corrienteRms = i < umbralRuido() ? 0 : i;
    } else corrienteRms = 0;
    muestrasPorSegundo = nMuestras * 1000UL / (ahora - inicioVentana);
  }
  inicioVentana = ahora; sumaV = sumaV2 = 0; nMuestras = 0;
}

/* ========================================================================== */
/*  PROTECCIONES                                                              */
/* ========================================================================== */
void actualizarTermica() {
  unsigned long ahora = millis();
  float dt = (ahora - instanteTermica) / 1000.0f;
  if (dt < 0.1f) return;
  instanteTermica = ahora;
  if (corrienteNominalA <= 0) { theta = 0; return; }
  float r = corrienteRms / corrienteNominalA;
  theta += dt / (float)TAU_TERMICA_S * (r * r - theta);
  if (theta < 0) theta = 0;
  if (estado != MARCHA) return;
  if (theta >= THETA_DISPARO) { activarFallo("SOBRECARGA_I2T"); return; }
  if (theta >= THETA_ADVERTENCIA && !advertenciaTermica) { advertenciaTermica = true; publicarAlarma("ADVERTENCIA_TERMICA"); }
  else if (theta < THETA_ADVERTENCIA && advertenciaTermica) { advertenciaTermica = false; publicarAlarma("SIN_ALARMA"); }
}

void verificarSobrecorriente() {
  if (estado != MARCHA || corrienteNominalA <= 0 || millis() - instanteEstado < 1000) { temporizandoSobrecorriente = false; return; }
  if (corrienteRms >= FACTOR_SOBRECORRIENTE * corrienteNominalA) {
    if (!temporizandoSobrecorriente) { temporizandoSobrecorriente = true; instanteSobrecorriente = millis(); }
    else if (millis() - instanteSobrecorriente >= TIEMPO_SOBRECORRIENTE_MS) activarFallo("SOBRECORRIENTE");
  } else temporizandoSobrecorriente = false;
}

/* El V20 dice que está en marcha y aplica más de 5 Hz, pero en la fase medida
 * no circula corriente: fase abierta, conexión floja del motor o corte aguas
 * abajo. Siempre hay al menos corriente de magnetización (30–50 % de In). */
void verificarPerdidaCorriente() {
  bool vigilar = vigilarPerdida && sensorOK && estado == MARCHA && v20Marcha &&
                 consignaAplicada >= F_MIN_VIGILANCIA_HZ &&
                 millis() - instanteEstado >= INHIBICION_PERDIDA_MS + ventanaMs();
  if (!vigilar) { temporizandoPerdida = false; return; }
  float umbral = UMBRAL_PERDIDA_A;
  if (corrienteNominalA > 0 && FRACCION_PERDIDA * corrienteNominalA > umbral) umbral = FRACCION_PERDIDA * corrienteNominalA;
  if (corrienteRms < umbral) {
    if (!temporizandoPerdida) { temporizandoPerdida = true; instantePerdida = millis(); }
    else if (millis() - instantePerdida >= TIEMPO_PERDIDA_MS) activarFallo("PERDIDA_CORRIENTE_FASE");
  } else temporizandoPerdida = false;
}

void verificarComunicacion() {
  if (enlaceOK() || !(estado == MARCHA && marchaRemota)) { instantePerdidaCom = 0; return; }
  if (instantePerdidaCom == 0) { instantePerdidaCom = millis(); Serial.println("Enlace perdido en marcha remota..."); return; }
  if (millis() - instantePerdidaCom >= TIMEOUT_COMUNICACION_MS) { instantePerdidaCom = 0; activarFallo("PERDIDA_COMUNICACION"); }
}

/* ========================================================================== */
/*  ÓRDENES (comunes a MQTT y consola)                                        */
/* ========================================================================== */
bool aplicarConfig(String clave, float valor) {
  clave.toLowerCase();
  if (clave == "rampa" && valor >= 0 && valor <= 120) rampaEspS = valor;
  else if (clave == "fmin" && valor >= 0 && valor <= fMaxHz) fMinHz = valor;
  else if (clave == "fmax" && valor >= fMinHz && valor <= 60) fMaxHz = valor;
  else if (clave == "in" && valor >= 0 && valor <= 30) { corrienteNominalA = valor; theta = 0; }
  else if (clave == "vigilancia") vigilarPerdida = valor > 0.5f;
  else return false;
  Serial.printf("Config %s = %.2f\n", clave.c_str(), valor);
  return true;
}

void procesarOrden(String o, bool remota) {
  o.trim(); o.toUpperCase();
  if      (o == "START" || o == "MARCHA")     iniciarMarcha(remota);
  else if (o == "STOP"  || o == "PARO")       detener();
  else if (o == "EMERGENCY" || o == "EMERG")  activarFallo(remota ? "PARADA_EMERGENCIA_APP" : "PARADA_EMERGENCIA_LOCAL");
  else if (o == "RESET")                      rearmar();
  else if (o == "FWD"  || o == "ADELANTE")    cambiarSentido(false);
  else if (o == "REV"  || o == "ATRAS")       cambiarSentido(true);
  else if (o == "PERFIL")                     iniciarPerfil();
  else if (o == "PERFIL_STOP")                { perfilActivo = false; consignaHz = 0; }
  else if (o == "CALIBRATE" || o == "CAL")    iniciarCalibracion();
  else publicarAviso("ORDEN_INVALIDA");
}

void fijarConsigna(float f, const char* origen) {
  if (isnan(f)) { publicarAviso("CONSIGNA_INVALIDA"); return; }
  perfilActivo = false;
  consignaHz = (f < 0) ? 0 : (f > F_REF ? F_REF : f);
  Serial.printf("t=%lu ms | consigna %.2f Hz (%s)\n", millis(), consignaHz, origen);
}

void callbackMQTT(char* topic, byte* payload, unsigned int len) {
  if (len > 48) len = 48;
  String m; m.reserve(len + 1);
  for (unsigned int i = 0; i < len; i++) m += (char)payload[i];
  m.trim();
  String t(topic);
  if (millis() - instanteSuscripcion < VENTANA_RETENIDOS_MS && (t == TOPIC_CMD || t == TOPIC_CONSIGNA)) {
    publicarAviso("ORDEN_IGNORADA_RECONEXION");   /* posible mensaje retenido */
    return;
  }
  if (t == TOPIC_CMD) procesarOrden(m, true);
  else if (t == TOPIC_CONSIGNA) fijarConsigna(m.toFloat(), "app");
  else if (t == TOPIC_CONFIG) {
    int eq = m.indexOf('=');
    if (eq < 1 || !aplicarConfig(m.substring(0, eq), m.substring(eq + 1).toFloat())) publicarAviso("CONFIG_INVALIDA");
  }
}

/* ========================================================================== */
/*  COMUNICACIONES                                                            */
/* ========================================================================== */
void iniciarWiFi() {
  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true); WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  ultimoIntentoWiFi = millis();
}

void mantenerWiFi() {
  if (WiFi.status() == WL_CONNECTED || millis() - ultimoIntentoWiFi < INTERVALO_WIFI_MS) return;
  ultimoIntentoWiFi = millis();
  WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void conectarMQTT() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (ultimoIntentoMQTT != 0 && millis() - ultimoIntentoMQTT < INTERVALO_MQTT_MS) return;
  ultimoIntentoMQTT = millis();
  String id = "ESP32-V20-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.print("Conectando a MQTT... ");
  if (!mqtt.connect(id.c_str(), MQTT_USER, MQTT_PASSWORD, TOPIC_ONLINE, 1, true, "OFFLINE")) {
    Serial.printf("falló (%d)\n", mqtt.state()); return;
  }
  Serial.println("conectado.");
  mqtt.subscribe(TOPIC_CMD, 1); mqtt.subscribe(TOPIC_CONSIGNA, 1); mqtt.subscribe(TOPIC_CONFIG, 1);
  instanteSuscripcion = millis();
  mqtt.publish(TOPIC_ONLINE, "ONLINE", true);
  publicarEstado();
  mqtt.publish(TOPIC_ALARMA, ultimaAlarma, true);
}

void publicarTelemetria() {
  if (!mqtt.connected() || millis() - ultimaTelemetria < INTERVALO_TELEMETRIA_MS) return;
  ultimaTelemetria = millis();
  char j[700];
  snprintf(j, sizeof(j),
    "{\"estado\":\"%s\",\"alarma\":\"%s\",\"f_cons\":%.2f,\"f_apl\":%.2f,\"v_ai1\":%.3f,"
    "\"duty\":%d,\"sentido\":\"%s\",\"di1\":%d,\"di2\":%d,\"v20_marcha\":%d,\"v20_falla\":%d,"
    "\"corriente\":%.2f,\"in_a\":%.2f,\"theta\":%.3f,\"sensor_ok\":%d,\"v_media\":%.3f,"
    "\"ruido_a\":%.3f,\"rampa_s\":%.1f,\"fmin\":%.1f,\"fmax\":%.1f,\"vigilancia\":%d,"
    "\"perfil\":%d,\"remota\":%d,\"muestras_s\":%lu,\"rssi\":%d,\"uptime_s\":%lu}",
    nombreEstado(estado), ultimaAlarma, consignaHz, (estado == FALLO) ? 0.0f : consignaAplicada,
    V_FS * dutyActual / D_MAX, dutyActual, sentidoInverso ? "ATRAS" : "ADELANTE",
    estado == MARCHA, sentidoInverso, v20Marcha, v20Falla, corrienteRms, corrienteNominalA,
    theta, sensorOK, voltajeMedio, ruidoA, rampaEspS, fMinHz, fMaxHz, vigilarPerdida,
    perfilActivo ? pasoPerfil + 1 : 0, marchaRemota, muestrasPorSegundo, (int)WiFi.RSSI(),
    millis() / 1000UL);
  mqtt.publish(TOPIC_TELEMETRIA, j, false);
}

/* ========================================================================== */
/*  CONSOLA SERIE (funciona sin red)                                          */
/* ========================================================================== */
void ayuda() {
  Serial.println("Consola: 0..60 (Hz) | marcha | paro | emerg | reset | adelante | atras");
  Serial.println("         p (perfil) | s (para perfil, 0 Hz) | cal | i (estado) | d (diagnóstico)");
  Serial.println("         rampa=5 | fmin=0 | fmax=60 | in=3.2 | vigilancia=1");
}

void diagnostico() {
  Serial.printf("ACS712: media %.3f V | cero %.3f V (%s) | ruido %.3f A | umbral %.3f A | %lu muestras/s | ventana %lu ms | sensor %s\n",
                voltajeMedio, voltajeCero, calibracionValida ? "válido" : "NO válido", ruidoA,
                umbralRuido(), muestrasPorSegundo, ventanaMs(), sensorOK ? "OK" : "FALLA");
  Serial.printf("Red: WiFi %s | MQTT %s | In %.2f A | theta %.3f | vigilancia %d\n",
                WiFi.status() == WL_CONNECTED ? "OK" : "NO", mqtt.connected() ? "OK" : "NO",
                corrienteNominalA, theta, vigilarPerdida);
}

bool esNumero(const String& s) {
  bool punto = false, dig = false;
  for (unsigned i = 0; i < s.length(); i++) {
    char c = s[i];
    if (isDigit(c)) dig = true;
    else if ((c == '.' || c == ',') && !punto) punto = true;
    else return false;
  }
  return dig;
}

void procesarSerial() {
  if (!Serial.available()) return;
  String c = Serial.readStringUntil('\n');
  c.trim();
  if (c.length() == 0) return;
  String l = c; l.toLowerCase();
  if (esNumero(c)) { c.replace(',', '.'); fijarConsigna(c.toFloat(), "consola"); }
  else if (l == "p") iniciarPerfil();
  else if (l == "s") { perfilActivo = false; fijarConsigna(0, "consola"); }
  else if (l == "i") mostrarEstado();
  else if (l == "d") diagnostico();
  else if (l == "?") ayuda();
  else if (l.indexOf('=') > 0) {
    int eq = l.indexOf('=');
    if (!aplicarConfig(l.substring(0, eq), l.substring(eq + 1).toFloat())) Serial.println("Config no válida");
  }
  else procesarOrden(c, false);
}

void actualizarLed() {
  unsigned long iv = estado == FALLO ? 100 : (estado == MARCHA ? 500 : 1000);
  if (millis() - instanteLed >= iv) { instanteLed = millis(); estadoLed = !estadoLed; digitalWrite(PIN_LED, estadoLed); }
}

/* ========================================================================== */
/*  SETUP Y LOOP                                                              */
/* ========================================================================== */
void setup() {
  /* Relés en reposo ANTES de habilitar las salidas: ningún DI del V20 se activa. */
  digitalWrite(PIN_DI1, RELE_OFF); digitalWrite(PIN_DI2, RELE_OFF); digitalWrite(PIN_DI3, RELE_OFF);
  pinMode(PIN_DI1, OUTPUT); pinMode(PIN_DI2, OUTPUT); pinMode(PIN_DI3, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_DO1, INPUT);          /* pull-up externo de 10 kΩ */
  pinMode(PIN_DO2, INPUT_PULLUP);
  pinMode(PIN_SENSOR, INPUT);
  pwmInit();

  Serial.begin(115200);
  Serial.setTimeout(50);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_SENSOR, ADC_11db);

  Serial.println();
  Serial.println("=== V20 IoT v3.0 | consigna AI1 + DI/DO + ACS712 + MQTT ===");
  ayuda();

#ifdef MQTT_CA_CERT
  clienteSeguro.setCACert(MQTT_CA_CERT);
#else
  clienteSeguro.setInsecure();
#endif
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(callbackMQTT);
  mqtt.setBufferSize(1024);
  mqtt.setKeepAlive(30);

  lecturaDO1 = v20Marcha = (digitalRead(PIN_DO1) == LOW);
  lecturaDO2 = v20Falla  = (digitalRead(PIN_DO2) == LOW);
  instanteRampa = instanteTermica = inicioVentana = millis();

  Serial.printf("Motivo del reinicio: %d\n", (int)esp_reset_reason());
  if (BLOQUEO_TRAS_REINICIO) { cambiarEstado(FALLO); publicarAlarma("RETORNO_ALIMENTACION"); }
  else cambiarEstado(DETENIDO);

  iniciarCalibracion();
  iniciarWiFi();
}

void loop() {
  leerEntradas();
  mantenerWiFi();
  conectarMQTT();
  if (mqtt.connected()) mqtt.loop();
  procesarSerial();

  atenderPerfil();
  actualizarRampa();
  atenderReconocimiento();
  aplicarSalidas();

  actualizarCorriente();
  actualizarTermica();
  verificarSobrecorriente();
  verificarPerdidaCorriente();
  verificarRespuestaV20();
  verificarComunicacion();

  publicarTelemetria();
  actualizarLed();
}
