#pragma once
#include "Arduino.h"
#define WL_CONNECTED 3
#define WIFI_STA 1
extern bool simRedActiva;
struct WiFiSim {
  void mode(int) {}
  void setAutoReconnect(bool) {}
  void persistent(bool) {}
  void begin(const char*, const char*) {}
  void disconnect() {}
  int status() { return simRedActiva ? WL_CONNECTED : 0; }
  int RSSI() { return simRedActiva ? -58 : 0; }
};
extern WiFiSim WiFi;
