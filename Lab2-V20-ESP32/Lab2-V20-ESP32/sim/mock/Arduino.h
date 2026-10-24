// Núcleo Arduino simulado para ejecutar el firmware del ESP32 en un PC.
// Las E/S se conectan a un modelo del V20 y del motor (planta.cpp).
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cctype>
#include <string>
#include <cstdarg>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define HEX 16
#define ADC_11db 3
typedef uint8_t byte;

unsigned long millis();
unsigned long micros();
void pinMode(int pin, int mode);
void digitalWrite(int pin, int v);
int digitalRead(int pin);
uint32_t analogReadMilliVolts(int pin);
inline void analogReadResolution(int) {}
inline void analogSetPinAttenuation(int, int) {}
bool ledcSetup(int ch, uint32_t f, int bits);
void ledcAttachPin(int pin, int ch);
void ledcWrite(int ch, uint32_t duty);
inline bool isDigit(char c) { return std::isdigit((unsigned char)c); }

class String {
 public:
  std::string s;
  String() {}
  String(const char* c) : s(c ? c : "") {}
  String(const std::string& x) : s(x) {}
  String(char c) : s(1, c) {}
  String(uint32_t v, int base) { char t[24]; snprintf(t, sizeof t, base == 16 ? "%x" : "%u", v); s = t; }
  void reserve(unsigned) {}
  unsigned length() const { return s.size(); }
  char operator[](unsigned i) const { return s[i]; }
  String& operator+=(char c) { s += c; return *this; }
  String& operator+=(const String& o) { s += o.s; return *this; }
  String operator+(const String& o) const { return String(s + o.s); }
  bool operator==(const char* c) const { return s == c; }
  bool operator==(const String& o) const { return s == o.s; }
  void trim() {
    size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
    s = (a == std::string::npos) ? "" : s.substr(a, b - a + 1);
  }
  void toUpperCase() { for (auto& c : s) c = std::toupper((unsigned char)c); }
  void toLowerCase() { for (auto& c : s) c = std::tolower((unsigned char)c); }
  int indexOf(char c) const { size_t p = s.find(c); return p == std::string::npos ? -1 : (int)p; }
  String substring(unsigned a) const { return a >= s.size() ? String() : String(s.substr(a)); }
  String substring(unsigned a, unsigned b) const { return String(s.substr(a, b - a)); }
  float toFloat() const { return (float)atof(s.c_str()); }
  long toInt() const { return atol(s.c_str()); }
  void replace(char a, char b) { for (auto& c : s) if (c == a) c = b; }
  const char* c_str() const { return s.c_str(); }
};
inline String operator+(const char* a, const String& b) { return String(std::string(a) + b.s); }

class SerialSim {
 public:
  void begin(int) {}
  void setTimeout(int) {}
  int available();
  String readStringUntil(char);
  void print(const char* t);
  void print(const String& t) { print(t.c_str()); }
  void print(float v, int d = 2) { char b[32]; snprintf(b, sizeof b, "%.*f", d, v); print(b); }
  void println() { print("\n"); }
  void println(const char* t) { print(t); print("\n"); }
  void println(const String& t) { println(t.c_str()); }
  void println(unsigned long v) { char b[32]; snprintf(b, sizeof b, "%lu", v); println(b); }
  void printf(const char* fmt, ...) {
    char b[1024]; va_list ap; va_start(ap, fmt); vsnprintf(b, sizeof b, fmt, ap); va_end(ap); print(b);
  }
};
extern SerialSim Serial;

struct EspSim { uint64_t getEfuseMac() { return 0x24A1B2C3D4E5ULL; } };
extern EspSim ESP;
