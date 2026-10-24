// PubSubClient simulado: el tráfico MQTT sale por stdout y entra por stdin.
// El orquestador en Python (run_sim.py) lo conecta a un broker MQTT real.
#pragma once
#include "Arduino.h"
#include "WiFiClientSecure.h"
typedef void (*CallbackMQTT)(char*, uint8_t*, unsigned int);
extern bool simRedActiva;
void simEmitir(const std::string& linea);
bool simSiguienteMensaje(std::string& topic, std::string& payload);

class PubSubClient {
  bool conectado = false;
  CallbackMQTT cb = nullptr;
 public:
  PubSubClient(WiFiClientSecure&) {}
  void setServer(const char*, int) {}
  void setCallback(CallbackMQTT c) { cb = c; }
  void setBufferSize(int) {}
  void setKeepAlive(int) {}
  bool connect(const char* id, const char*, const char*, const char* willT, int, bool, const char* willM) {
    if (!simRedActiva) return false;
    conectado = true;
    simEmitir(std::string("CON ") + id + " " + willT + " " + willM);
    return true;
  }
  bool connected() { if (!simRedActiva) conectado = false; return conectado; }
  int state() { return conectado ? 0 : -2; }
  bool subscribe(const char* t, int) { if (!connected()) return false; simEmitir(std::string("SUB ") + t); return true; }
  bool publish(const char* t, const char* p, bool r) {
    if (!connected()) return false;
    simEmitir(std::string("PUB ") + (r ? "1 " : "0 ") + t + " " + p);
    return true;
  }
  void loop() {
    std::string t, p;
    while (connected() && simSiguienteMensaje(t, p)) {
      std::string tc = t, pc = p;
      cb(&tc[0], (uint8_t*)&pc[0], (unsigned)pc.size());
    }
  }
};
