# PCB una cara — interfaz ESP32 ↔ SINAMICS V20 (firmware v3.2)

- `salida/PCB_V20IoT_planchado_1a1.pdf`: cobre 1:1 para planchado (2 copias), mapa de montaje, puentes y armado.
- `salida/V20IoT_gerber.zip`: Gerber RS-274X + Excellon (cobre inferior, máscara, serigrafía, borde, taladros).
- `salida/netlist_V20IoT.csv`: referencia, valor, pin y red de cada pad (para capturar el esquema en Proteus).

Regenerar: `python3 ejecutar.py 40 && python3 salida.py && python3 verificar_gerber.py && python3 pdf_planchado.py`

`verificar_gerber.py` lee el Gerber de cobre, lo rasteriza a 0,025 mm y compara islas de cobre con el netlist:
cortos, aberturas, holgura < 0,4 mm y taladros sin cobre.
