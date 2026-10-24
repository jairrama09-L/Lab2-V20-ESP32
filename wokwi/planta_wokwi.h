/* =============================================================================
 *  planta_wokwi.h — V20 y motor simulados DENTRO del ESP32, para probar el
 *  firmware en Wokwi sin variador. Solo se incluye si credenciales.h define
 *  SIMULACION_WOKWI. El firmware no cambia: aquí se redirigen sus E/S.
 *
 *  Lo que simula:
 *   - V20: lee DI1 (GPIO26), DI2 (GPIO27), DI3 (GPIO32) y la consigna PWM
 *     (GPIO25); rampas P1120 = P1121 = 10 s; DO1 "en marcha" y DO2 "falla".
 *   - Motor: corriente de vacío 1,4 A + aceleración + carga (potenciómetro).
 *   - ACS712-30A en la fase U: senoide a la frecuencia de salida + ruido.
 *
 *  Controles en el diagrama de Wokwi:
 *   GPIO18 botón      "FALLA V20"        (la falla se borra con RESET → DI3)
 *   GPIO19 interruptor "CORTE DE RED"
 *   GPIO21 interruptor "FASE ABIERTA"
 *   GPIO22 interruptor "SENSOR DESCONECTADO"
 *   VP (36) potenciómetro "CARGA" 0 … 3 A
 *   LED GPIO16 = V20 en marcha · LED GPIO17 = V20 en falla
 *   LED GPIO26/27/32 = PC817 DI1/DI2/DI3 · LED GPIO25 = brillo ∝ consigna
 * =============================================================================
 */
#pragma once
#include <math.h>

#define RELE_ACTIVO_BAJO 0          /* igual que con PC817: ALTO = activo */
#define TAU_TERMICA_S    60         /* I²t más rápido para verlo en la simulación    */

namespace planta {
  const uint8_t BTN_FALLA = 18, SW_RED = 19, SW_FASE = 21, SW_SENSOR = 22, POT_CARGA = 36;
  const uint8_t LED_MARCHA = 16, LED_FALLA = 17;
  bool iniciada = false, falla = false, enMarcha = false, di3Prev = false;
  bool di1 = false, di2 = false, di3 = false;
  uint32_t duty = 0;
  double f = 0, fase = 0, iRms = 0, tPrev = 0, cargaA = 0;
  unsigned long ultimoInforme = 0, ultimoPot = 0;
  const double P1120 = 10, P1121 = 10, P1082 = 60;

  void iniciar() {
    pinMode(BTN_FALLA, INPUT_PULLUP); pinMode(SW_RED, INPUT_PULLUP);
    pinMode(SW_FASE, INPUT_PULLUP);   pinMode(SW_SENSOR, INPUT_PULLUP);
    pinMode(LED_MARCHA, OUTPUT);      pinMode(LED_FALLA, OUTPUT);
    tPrev = micros() / 1e6; iniciada = true;
  }

  void actualizar() {
    if (!iniciada) iniciar();
    double t = micros() / 1e6, dt = t - tPrev;
    if (dt <= 0) return;
    tPrev = t;
    bool red = digitalRead(SW_RED) == HIGH;            /* interruptor a GND = corte  */
    if (digitalRead(BTN_FALLA) == LOW) falla = true;
    if (di3 && !di3Prev && falla && !di1) falla = false; /* reconocimiento por DI3   */
    di3Prev = di3;
    if (millis() - ultimoPot > 100) { ultimoPot = millis(); cargaA = analogRead(POT_CARGA) / 4095.0 * 3.0; }

    double fPrev = f;
    if (!red || falla) {
      enMarcha = false; f *= exp(-dt / 1.5); if (fabs(f) < 0.05) f = 0;
    } else {
      double fset = 60.0 * duty / 1023.0;
      double obj = di1 ? (di2 ? -fset : fset) : 0.0;
      bool acel = fabs(obj) > fabs(f) && obj * f >= 0;
      double paso = P1082 / (acel ? P1120 : P1121) * dt;
      if (fabs(obj - f) <= paso) f = obj; else f += (obj > f) ? paso : -paso;
      enMarcha = di1 || fabs(f) > 0.01;
      if (!di1 && fabs(f) <= 0.01) { f = 0; enMarcha = false; }
    }
    double dfdt = (f - fPrev) / dt;
    fase += 2 * M_PI * fabs(f) * dt;
    if (fase > 1e6) fase = fmod(fase, 2 * M_PI);
    double iAct = 0.15 * fabs(dfdt) + cargaA;
    iRms = enMarcha ? sqrt(1.40 * 1.40 + iAct * iAct) : 0;

    digitalWrite(LED_MARCHA, enMarcha); digitalWrite(LED_FALLA, falla);
    if (millis() - ultimoInforme >= 1000) {
      ultimoInforme = millis();
      Serial.printf("[V20 simulado] f = %+6.2f Hz | I real = %.2f A | carga %.2f A | %s%s%s%s\n",
                    f, iRms, cargaA, enMarcha ? "EN MARCHA" : "parado", falla ? " | FALLA" : "",
                    red ? "" : " | SIN RED", digitalRead(SW_FASE) == LOW ? " | FASE ABIERTA" : "");
    }
  }

  int leerDigital(uint8_t p) {
    actualizar();
    if (p == 35) return enMarcha ? LOW : HIGH;   /* DO1 */
    if (p == 33) return falla ? LOW : HIGH;      /* DO2 */
    return digitalRead(p);
  }

  void escribirDigital(uint8_t p, uint8_t v) {
    if (p == 26) di1 = v; else if (p == 27) di2 = v; else if (p == 32) di3 = v;
    digitalWrite(p, v);
  }

  uint32_t leerMilivoltios(uint8_t) {
    actualizar();
    static uint32_t semilla = 12345;
    semilla = semilla * 1103515245u + 12345u;
    double ruido = ((int)((semilla >> 8) % 2001u) - 1000) / 1000.0 * 0.017;   /* ≈ 10 mV rms */
    double v;
    if (digitalRead(SW_SENSOR) == LOW) v = 0.0;
    else {
      bool abierta = digitalRead(SW_FASE) == LOW;
      v = 2.5 + (abierta ? 0.0 : 0.066 * sqrt(2.0) * iRms * sin(fase)) + ruido;
    }
    double mv = v * 2.0 / 3.0 * 1000.0;
    return mv < 0 ? 0 : (uint32_t)mv;
  }
}

/* Redirección de las E/S del firmware hacia la planta simulada.
 * Las funciones de arriba usan las originales porque se definen antes. */
template <typename A, typename B> inline void planta_ledcWrite(A a, B b) { planta::duty = (uint32_t)b; ledcWrite(a, b); }
#define digitalRead(p)          planta::leerDigital(p)
#define digitalWrite(p, v)      planta::escribirDigital((p), (v))
#define analogReadMilliVolts(p) planta::leerMilivoltios(p)
#define ledcWrite(a, b)         planta_ledcWrite((a), (b))
