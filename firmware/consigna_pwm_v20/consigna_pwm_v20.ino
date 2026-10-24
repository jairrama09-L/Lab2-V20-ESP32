/*
 * ============================================================================
 *  consigna_pwm_v20.ino  —  versión 2.0 (basada en el firmware de la Guía N.º 2)
 *  Consigna analógica 0–10 V para el SINAMICS V20 generada por PWM desde un ESP32
 *  Laboratorio N.º 2 — Electrónica de Potencia, Universidad del Magdalena, 2026-II
 * ============================================================================
 *
 *  CADENA DE SEÑAL
 *    GPIO25 (PWM 20 kHz, 10 bit) -> 220 Ω -> LED 6N137 | barrera de aislamiento |
 *    6N137 (invierte) -> 74HC14 (invierte, fija VH = 5 V) -> RC 10 kΩ/1 µF (fc = 15,9 Hz)
 *    -> LM358 no inversor (G = 2) -> 100 Ω + Zener 12 V -> AI1 del V20
 *    Dos inversiones => la cadena completa NO invierte:  V_AI1 = 10 · D  [V]
 *
 *  ESTADO SEGURO
 *    Con el ESP32 en reset, sin firmware o sin USB, el GPIO25 queda en alta impedancia:
 *    LED apagado -> salida 6N137 en alto -> 74HC14 en bajo -> V_AI1 = 0 V -> 0 Hz.
 *
 *  ESCALADO
 *    El firmware solo fija el ciclo de trabajo D = f / F_REF. La conversión V -> Hz la
 *    hace el V20 (P0757..P0760, P2000). La calibración se hace en P0759[0] = r0752 @ 60 Hz,
 *    NO en el firmware.
 *
 *  COMPATIBILIDAD
 *    Núcleo Arduino-ESP32 2.0.x (recomendado por la guía: 2.0.17) y 3.x (API LEDC nueva).
 *    Placa: "ESP32 Dev Module". Monitor serie: 115200 baudios, fin de línea "Nueva línea".
 *
 *  COMANDOS (monitor serie)
 *    0..60     fija la consigna en Hz (admite decimales: 12.5)
 *    p         perfil de escalones 0-15-30-45-60-30-0 Hz, 20 s cada uno (no bloqueante)
 *    s         detiene el perfil y lleva la consigna a 0 Hz
 *    i         imprime el estado actual
 *    ?         ayuda
 *    Cada cambio de consigna imprime una marca de tiempo t[ms] para cronometrar rampas.
 *
 *  CAMBIOS FRENTE A LA VERSIÓN DE LA GUÍA
 *    - Perfil no bloqueante (máquina de estados con millis()): 's' se atiende siempre.
 *    - Compila en núcleo 2.x y 3.x.
 *    - Marca de tiempo en cada cambio de consigna (apoyo a la Tabla 2).
 *    - Validación de entrada (rechaza texto, negativos y valores > 60 se saturan).
 * ============================================================================
 */
#include <Arduino.h>

// ---------------- Parámetros de diseño ----------------
const int      PIN_PWM     = 25;
const int      CANAL       = 0;          // solo se usa en núcleo 2.x
const uint32_t F_PWM       = 20000;      // frecuencia del PWM [Hz]
const uint8_t  BITS        = 10;         // resolución: 0..1023
const int      D_MAX       = (1 << BITS) - 1;
const float    F_REF       = 60.0f;      // Hz que corresponden a D = 100 % (P2000 del V20)
const float    V_FS        = 10.0f;      // tensión nominal en AI1 con D = 100 %
const uint32_t T_ESCALON_MS = 20000;     // duración de cada escalón del perfil

const float PASOS[] = {0, 15, 30, 45, 60, 30, 0};
const int   N_PASOS = sizeof(PASOS) / sizeof(PASOS[0]);

// ---------------- Estado ----------------
float    consigna   = 0.0f;
int      dutyActual = 0;
bool     perfilActivo = false;
int      pasoActual = 0;
uint32_t tPaso      = 0;

// ---------------- Capa de hardware (2.x / 3.x) ----------------
void pwmInit() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(PIN_PWM, F_PWM, BITS);
#else
  ledcSetup(CANAL, F_PWM, BITS);
  ledcAttachPin(PIN_PWM, CANAL);
#endif
}

void pwmWrite(int d) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(PIN_PWM, d);
#else
  ledcWrite(CANAL, d);
#endif
}

// ---------------- Lógica ----------------
void fijarConsigna(float f_hz) {
  consigna   = constrain(f_hz, 0.0f, F_REF);
  dutyActual = (int)lroundf(consigna / F_REF * D_MAX);
  pwmWrite(dutyActual);
  Serial.printf("t=%8lu ms | Consigna %5.2f Hz | ciclo %4d/%d (%6.2f %%) | AI1 esperada %5.3f V\n",
                (unsigned long)millis(), consigna, dutyActual, D_MAX,
                100.0f * dutyActual / D_MAX, V_FS * dutyActual / D_MAX);
}

void iniciarPerfil() {
  perfilActivo = true;
  pasoActual = 0;
  tPaso = millis();
  Serial.println("Perfil de escalones iniciado (enviar 's' para detener)");
  fijarConsigna(PASOS[0]);
}

void detenerPerfil(const char* motivo) {
  perfilActivo = false;
  fijarConsigna(0);
  Serial.println(motivo);
}

void atenderPerfil() {
  if (!perfilActivo) return;
  if (millis() - tPaso < T_ESCALON_MS) return;
  pasoActual++;
  if (pasoActual >= N_PASOS) {
    perfilActivo = false;
    Serial.println("Perfil terminado");
    return;
  }
  tPaso = millis();
  fijarConsigna(PASOS[pasoActual]);
}

void ayuda() {
  Serial.println("Comandos: 0..60 (Hz) | p = perfil | s = parar | i = estado | ? = ayuda");
}

void estado() {
  Serial.printf("Consigna %.2f Hz | duty %d/%d | perfil %s (paso %d/%d)\n",
                consigna, dutyActual, D_MAX, perfilActivo ? "ACTIVO" : "inactivo",
                pasoActual + 1, N_PASOS);
}

bool esNumero(const String& s) {
  bool punto = false, digito = false;
  for (unsigned i = 0; i < s.length(); i++) {
    char c = s[i];
    if (isDigit(c)) digito = true;
    else if ((c == '.' || c == ',') && !punto) punto = true;
    else return false;
  }
  return digito;
}

void atenderSerie() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd == "p")      iniciarPerfil();
  else if (cmd == "s") detenerPerfil("Perfil detenido / consigna en 0 Hz");
  else if (cmd == "i") estado();
  else if (cmd == "?") ayuda();
  else if (esNumero(cmd)) {
    cmd.replace(',', '.');
    if (perfilActivo) { perfilActivo = false; Serial.println("Perfil cancelado por consigna manual"); }
    float f = cmd.toFloat();
    if (f > F_REF) Serial.println("Aviso: valor > 60 Hz, se satura en 60 Hz");
    fijarConsigna(f);
  }
  else Serial.println("Comando no reconocido ('?' para ayuda)");
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);
  pwmInit();
  fijarConsigna(0);                       // arranque seguro: 0 V en AI1
  Serial.println("Consigna PWM para V20 lista (v2.0).");
  ayuda();
}

void loop() {
  atenderSerie();
  atenderPerfil();
}
