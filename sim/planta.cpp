// Simulación del hardware alrededor del ESP32:
//  - E/S del microcontrolador (GPIO, ADC, LEDC) conectadas a
//  - un modelo del SINAMICS V20 (DI1 marcha, DI2 inversión, DI3 reconocimiento,
//    AI1 consigna, rampas P1120/P1121, DO1 en marcha, DO2 falla) y
//  - un modelo del motor (corriente de magnetización + aceleración + carga)
//    medido por un ACS712 en la fase U.
// Protocolo con el orquestador (stdin/stdout, una línea por mensaje):
//  entrada: "MSG <topic> <payload>" | "SER <texto>" | "NET 0|1" | "PLANTA <orden> [valor]"
//  salida : "LOG <texto>" | "PUB <r> <topic> <payload>" | "SUB <topic>" | "CON ..." | "CSV ..."
#include "Arduino.h"
#include "WiFi.h"
#include <chrono>
#include <deque>
#include <random>
#include <unistd.h>
#include <fcntl.h>
#include <thread>

void setup();
void loop();

SerialSim Serial;
EspSim ESP;
WiFiSim WiFi;
bool simRedActiva = true;

static auto T0 = std::chrono::steady_clock::now();
unsigned long micros() {
  return (unsigned long)std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - T0).count();
}
unsigned long millis() { return micros() / 1000UL; }

// ------------------------------------------------------------ E/S --------
static int salidas[40] = {0};  // pull-downs
static int dutyPWM = 0;
bool ledcSetup(int, uint32_t, int) { return true; }
void ledcAttachPin(int, int) {}
void ledcWrite(int, uint32_t d) { dutyPWM = (int)d; }
void pinMode(int, int) {}
void digitalWrite(int p, int v) { if (p >= 0 && p < 40) salidas[p] = v; }

// ------------------------------------------------------- Modelo V20 -------
struct V20 {
  double f = 0;            // frecuencia de salida con signo [Hz]
  double dfdt = 0;
  double fase = 0;         // ángulo eléctrico [rad]
  bool red = true, falla = false, faseAbierta = false, sensorConectado = true;
  bool enMarcha = false;   // estado de DO1 (52.2)
  double P1120 = 10, P1121 = 10, P1080 = 0, P1082 = 60;
  double cargaA = 0;       // componente activa de carga [A]
  bool di3Prev = false;
  double tUltimo = 0;
  double iRms = 0;         // corriente real de fase [A rms]
} v20;

static std::mt19937 rng(7);
static std::normal_distribution<double> ruido(0.0, 1.0);

static double ahoraS() { return micros() / 1e6; }

static void actualizarPlanta() {
  double t = ahoraS(), dt = t - v20.tUltimo;
  if (dt <= 0) return;
  v20.tUltimo = t;
#ifndef RELE_ACTIVO_BAJO
#define RELE_ACTIVO_BAJO 0
#endif
  // opto/relé activo = 24 V en el DI
  bool di1 = salidas[26] != RELE_ACTIVO_BAJO, di2 = salidas[27] != RELE_ACTIVO_BAJO, di3 = salidas[32] != RELE_ACTIVO_BAJO;
  // DI3: flanco de subida con DI1 abierto reconoce la falla
  if (di3 && !v20.di3Prev && v20.falla && !di1) v20.falla = false;
  v20.di3Prev = di3;

  double fPrev = v20.f;
  if (!v20.red || v20.falla) {               // pulsos bloqueados: el motor gira libre
    v20.enMarcha = false;
    v20.f *= exp(-dt / 1.5);
    if (fabs(v20.f) < 0.05) v20.f = 0;
  } else {
    double fset = 60.0 * dutyPWM / 1023.0;   // AI1 calibrada: f = P2000·V/P0759
    if (fset < v20.P1080) fset = v20.P1080;
    if (fset > v20.P1082) fset = v20.P1082;
    double objetivo = di1 ? (di2 ? -fset : fset) : 0.0;
    bool acelera = fabs(objetivo) > fabs(v20.f) && (objetivo * v20.f >= 0);
    double tasa = v20.P1082 / (acelera ? v20.P1120 : v20.P1121);
    double paso = tasa * dt;
    if (fabs(objetivo - v20.f) <= paso) v20.f = objetivo;
    else v20.f += (objetivo > v20.f) ? paso : -paso;
    v20.enMarcha = di1 || fabs(v20.f) > 0.01;
    if (!di1 && fabs(v20.f) <= 0.01) { v20.f = 0; v20.enMarcha = false; }
  }
  v20.dfdt = (v20.f - fPrev) / dt;
  v20.fase += 2 * M_PI * fabs(v20.f) * dt;
  if (v20.enMarcha) {
    double iMag = 1.40;                             // corriente de vacío (magnetización)
    double iAcc = 0.15 * fabs(v20.dfdt);            // par de aceleración: J·dω/dt
    double iAct = iAcc + v20.cargaA;
    v20.iRms = sqrt(iMag * iMag + iAct * iAct);
  } else v20.iRms = 0;
}

int digitalRead(int p) {
  actualizarPlanta();
  if (p == 35) return v20.enMarcha ? LOW : HIGH;     // DO1 vía PC817 (activo bajo)
  if (p == 33) return v20.falla ? LOW : HIGH;        // relé DO2 (activo bajo)
  return HIGH;
}

uint32_t analogReadMilliVolts(int) {
  actualizarPlanta();
  double t = ahoraS();
  double v;
  if (!v20.sensorConectado) v = 0.0;
  else {
    double i = (v20.faseAbierta ? 0.0 : sqrt(2.0) * v20.iRms * sin(v20.fase));
    double portadora = v20.enMarcha && !v20.faseAbierta ? 0.003 * sin(2 * M_PI * 4000 * t) : 0;
    v = 2.5 + 0.066 * i + portadora + 0.010 * ruido(rng);   // salida del ACS712-30A
  }
  double mv = v * (20.0 / 30.0) * 1000.0;                   // divisor 10k/20k
  if (mv < 0) mv = 0;
  if (mv > 3100) mv = 3100;
  return (uint32_t)lround(mv);
}

// ------------------------------------------------------- E/S de texto -----
static std::string bufEntrada, bufSerieSalida;
static std::deque<std::string> serieEntrada;
static std::deque<std::pair<std::string, std::string>> mqttEntrada;

void simEmitir(const std::string& l) { fputs(l.c_str(), stdout); fputc('\n', stdout); fflush(stdout); }

void SerialSim::print(const char* t) {
  bufSerieSalida += t;
  size_t p;
  while ((p = bufSerieSalida.find('\n')) != std::string::npos) {
    simEmitir("LOG " + bufSerieSalida.substr(0, p));
    bufSerieSalida.erase(0, p + 1);
  }
}
int SerialSim::available() { return serieEntrada.empty() ? 0 : 1; }
String SerialSim::readStringUntil(char) {
  if (serieEntrada.empty()) return String();
  std::string l = serieEntrada.front(); serieEntrada.pop_front();
  return String(l);
}
bool simSiguienteMensaje(std::string& t, std::string& p) {
  if (mqttEntrada.empty()) return false;
  t = mqttEntrada.front().first; p = mqttEntrada.front().second; mqttEntrada.pop_front();
  return true;
}

static void ordenPlanta(const std::string& o) {
  char nombre[32] = {0}; double val = 0;
  sscanf(o.c_str(), "%31s %lf", nombre, &val);
  std::string n = nombre;
  if (n == "FALLA") v20.falla = true;
  else if (n == "RED") v20.red = val > 0.5;
  else if (n == "FASE_ABIERTA") v20.faseAbierta = val > 0.5;
  else if (n == "SENSOR") v20.sensorConectado = val > 0.5;
  else if (n == "CARGA") v20.cargaA = val;
  else if (n == "P1120") v20.P1120 = val;
  else if (n == "P1121") v20.P1121 = val;
  else if (n == "P1080") v20.P1080 = val;
  else if (n == "P1082") v20.P1082 = val;
  simEmitir("LOG [planta] " + o);
}

static void leerEntrada() {
  char b[4096];
  ssize_t n;
  while ((n = read(0, b, sizeof b)) > 0) bufEntrada.append(b, n);
  size_t p;
  while ((p = bufEntrada.find('\n')) != std::string::npos) {
    std::string l = bufEntrada.substr(0, p); bufEntrada.erase(0, p + 1);
    if (l.rfind("MSG ", 0) == 0) {
      size_t sp = l.find(' ', 4);
      std::string t = l.substr(4, sp == std::string::npos ? std::string::npos : sp - 4);
      std::string pl = sp == std::string::npos ? "" : l.substr(sp + 1);
      mqttEntrada.emplace_back(t, pl);
    } else if (l.rfind("SER ", 0) == 0) serieEntrada.push_back(l.substr(4));
    else if (l.rfind("NET ", 0) == 0) simRedActiva = l[4] == '1';
    else if (l.rfind("PLANTA ", 0) == 0) ordenPlanta(l.substr(7));
    else if (l == "SALIR") exit(0);
  }
}

int main() {
  fcntl(0, F_SETFL, fcntl(0, F_GETFL) | O_NONBLOCK);
  setup();
  double ultimoCsv = 0;
  while (true) {
    leerEntrada();
    actualizarPlanta();
    loop();
    double t = ahoraS();
    if (t - ultimoCsv >= 0.05) {
      ultimoCsv = t;
      char l[256];
      snprintf(l, sizeof l, "CSV %.3f,%d,%d,%d,%d,%.3f,%.3f,%d,%d,%d,%d",
               t, dutyPWM, (int)(salidas[26] != RELE_ACTIVO_BAJO), (int)(salidas[27] != RELE_ACTIVO_BAJO), (int)(salidas[32] != RELE_ACTIVO_BAJO), v20.f, v20.iRms,
               v20.enMarcha, v20.falla, v20.red, v20.faseAbierta);
      simEmitir(l);
    }
    std::this_thread::sleep_for(std::chrono::microseconds(40));
  }
}
int analogRead(int) { return 0; }
