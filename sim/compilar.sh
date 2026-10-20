#!/bin/sh
# Compila el firmware real del ESP32 para PC, con el hardware simulado (planta.cpp)
set -e
cd "$(dirname "$0")"
mkdir -p build
g++ -std=c++17 -O2 -DTAU_TERMICA_S=30 -Imock -x c++ ../firmware/v20_iot_esp32/v20_iot_esp32.ino planta.cpp -o build/esp32_sim -lpthread
echo "Listo: build/esp32_sim"
