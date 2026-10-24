// Genera el borrador del informe IEEE del Laboratorio 2 (Word, dos columnas)
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  AlignmentType, WidthType, BorderStyle, SectionType, ShadingType, LevelFormat,
  Footer, PageNumber,
} = require('docx');

const FIG = path.join(__dirname, 'figuras');
const FONT = 'Times New Roman';
const COLW = 5070; // ancho de columna en DXA

// ---------- helpers ----------
const t = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 20, bold: o.bold, italics: o.italics, smallCaps: o.smallCaps, superScript: o.sup, subScript: o.sub, color: o.color, highlight: o.hl });
const ph = (text) => t(text, { hl: 'yellow' }); // marcador pendiente
function P(runs, o = {}) {
  if (typeof runs === 'string') runs = [t(runs, o)];
  return new Paragraph({ children: runs, alignment: o.align || AlignmentType.JUSTIFIED, spacing: { after: o.after ?? 80, before: o.before ?? 0, line: 230 }, indent: o.noIndent ? undefined : { firstLine: 202 }, keepNext: o.keepNext });
}
let secN = 0; const ROMAN = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII'];
function H1(text) {
  return new Paragraph({ children: [t(`${ROMAN[secN++]}. ${text}`, { smallCaps: true })], alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, keepNext: true });
}
let subN = 0;
function H2(letter, text) {
  return new Paragraph({ children: [t(`${letter}. ${text}`, { italics: true })], spacing: { before: 120, after: 60 }, keepNext: true });
}
function EQ(text, num) {
  return new Paragraph({ children: [t(text, { italics: true }), t(`\t(${num})`)], tabStops: [{ type: 'right', position: COLW }], alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 } });
}
function img(file, wpx, hpx) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 40 }, keepNext: true,
    children: [new ImageRun({ type: 'png', data: fs.readFileSync(path.join(FIG, file)), transformation: { width: wpx, height: hpx } })] });
}
const cap = (text) => new Paragraph({ children: [t(text, { size: 16 })], alignment: AlignmentType.CENTER, spacing: { after: 140 } });
const tcap = (num, text) => [
  new Paragraph({ children: [t(`TABLA ${num}`, { size: 16, smallCaps: false })], alignment: AlignmentType.CENTER, spacing: { before: 120, after: 0 }, keepNext: true }),
  new Paragraph({ children: [t(text.toUpperCase(), { size: 16, smallCaps: true })], alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true }),
];
const bord = { style: BorderStyle.SINGLE, size: 4, color: '000000' };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
function table(rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER,
    rows: rows.map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true, children: r.map((c, j) => new TableCell({
      width: { size: widths[j], type: WidthType.DXA },
      margins: { top: 30, bottom: 30, left: 60, right: 60 },
      borders: { top: i === 0 ? bord : none, bottom: (i === 0 || i === rows.length - 1) ? bord : none, left: none, right: none },
      shading: i === 0 ? { type: ShadingType.CLEAR, fill: 'EDEDED', color: 'auto' } : undefined,
      children: [new Paragraph({ keepNext: i < rows.length - 1, alignment: j === 0 && !o.centerFirst ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: (Array.isArray(c) ? c : [c]).map(x => typeof x === 'string' ? t(x, { size: 16, bold: i === 0 }) : x) })],
    })) })),
  });
}
const PEND = () => ph('____');
const bullet = (runs) => new Paragraph({ children: typeof runs === 'string' ? [t(runs)] : runs, numbering: { reference: 'vin', level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { after: 40, line: 230 } });

const fimg = (file, w, h) => img(file, w, h);

// ---------- encabezado (una columna) ----------
const cab = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [t('Control de Velocidad y Supervisión IoT de un Motor de Inducción con SINAMICS V20 y ESP32: Consigna Analógica Aislada, Mando por Optoacopladores y Aplicación Móvil MQTT', { size: 40 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [ph('[Juan José — apellidos], [código], [correo]@unimagdalena.edu.co')] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [ph('[Nombre del compañero], [código], [correo]@unimagdalena.edu.co')] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [t('Electrónica de Potencia, ', { size: 18 }), ph('Grupo [__]'), t(' | Docente: Ing. Jordan Dallan Guillot Fula | Universidad del Magdalena | ', { size: 18 }), ph('[fecha de entrega]')] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [t('Repositorio GitHub: ', { size: 18 }), ph('[PEGAR AQUÍ EL ENLACE PÚBLICO]')] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: 220 }, children: [
    t('Resumen', { bold: true, italics: true, size: 18 }),
    t('—Se diseñó e implementó la interfaz entre un ESP32 y un variador SINAMICS V20 que reemplaza el potenciómetro de consigna y los pulsadores de mando del banco. La consigna de 0 a 10 V se obtiene de un PWM de 20 kHz y 10 bits aislado con un 6N137, reconstruido con un 74HC14, filtrado a 15,9 Hz y amplificado con ganancia 2 por un LM358: el diseño predice un rizado máximo de 12,5 mVpp (0,075 Hz) y una resolución de 9,8 mV (0,059 Hz). La marcha, la inversión y el reconocimiento de fallas se entregan a las entradas digitales de 24 V mediante tres optoacopladores PC817; el estado “en marcha” vuelve por un cuarto PC817 y la falla por el contacto seco del relé DO2. Un ACS712 mide la corriente de una fase. El firmware implementa una máquina de estados con siete protecciones y se comunica por MQTT sobre TLS con una aplicación web para el celular. Todo el circuito se montó en una tarjeta de una cara de 142 × 86 mm con barrera de aislamiento. La simulación del firmware real contra un modelo del variador y del motor superó 30 de 30 pruebas: la rampa de 0 a 30 Hz tardó 4,96 s frente a 5,00 s teóricos y la parada de emergencia abrió DI1 en 40 ms. ', { bold: true, size: 18 }),
    ph('[Completar con resultados de banco: error tras calibrar __ %, rizado medido __ mVpp, corriente app vs. r0027 __ %.]'),
  ] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 200 }, children: [t('Palabras clave', { bold: true, italics: true, size: 18 }), t('—aislamiento galvánico, ESP32, IoT, motor de inducción, MQTT, optoacoplador, PWM, SINAMICS V20, variador de frecuencia.', { bold: true, size: 18 })] }),
  fimg('esquematico_iot.png', 662, 431),
  cap('Fig. 1. Esquemático completo. Azul: dominio del ESP32 (fuente propia de 5 V, J11). Naranja: dominio del V20 (fuente externa de 5/12 V referida al borne 92 y salida de 24 V del variador). Solo los optoacopladores cruzan la barrera.'),
];

const cuerpo = [
  H1('Introducción'),
  P('En una instalación industrial la consigna y las órdenes de un variador provienen de un PLC o de un sistema de supervisión, no de un potenciómetro y pulsadores. Generarlas desde un microcontrolador conectado a la red permite repetir ensayos con valores exactos, aplicar perfiles de velocidad y vigilar el accionamiento a distancia. Este trabajo reemplaza el potenciómetro de AI1 de un SINAMICS V20 por una tensión de 0 a 10 V producida por un ESP32 y añade el mando y la supervisión del variador desde una aplicación móvil.'),
  P('Los objetivos fueron: diseñar el acondicionador PWM→0–10 V aislado y verificar su resolución, rizado y linealidad; calibrar AI1 para que 100 % de ciclo de trabajo corresponda a 60 Hz; evaluar el efecto de las rampas, los límites de frecuencia y la característica V/f; y, como ampliación, mandar las entradas DI1–DI3 del variador, leer sus salidas DO1 y DO2, medir la corriente de una fase y operar todo por MQTT con protecciones en el firmware, manteniendo el aislamiento galvánico entre el ESP32 y el variador.'),

  H1('Fundamento teórico'),
  H2('A', 'Velocidad del motor de inducción'),
  P('El estator crea un campo rotante cuya velocidad depende de la frecuencia f y del número de polos p; el rotor gira a una velocidad n algo menor y la diferencia relativa es el deslizamiento s:'),
  EQ('nₛ = 120·f / p,     s = (nₛ − n) / nₛ', 1),
  P('Para el motor de dos polos del módulo, nₛ = 3600 rpm a 60 Hz. Variar f desplaza la característica par–velocidad y el motor opera con bajo deslizamiento en todo el rango; la rampa evita la corriente de arranque directo, que puede superar siete veces la nominal.'),
  H2('B', 'Relación V/f'),
  P('El flujo en el entrehierro es proporcional a V/f. El variador ajusta la tensión según'),
  EQ('V(f) = V_boost + (Vₙ − V_boost)·f / fₙ', 2),
  P('con pendiente 220/60 ≈ 3,67 V/Hz. El refuerzo P1310 compensa la caída en la resistencia del estator a baja frecuencia; la característica cuadrática (P1300 = 2) reduce la tensión a velocidades intermedias para cargas de par cuadrático.'),
  H2('C', 'Del PWM a una tensión continua'),
  P('Un PWM de amplitud V_H y ciclo de trabajo D tiene valor medio D·V_H. Un filtro RC conserva ese valor y atenúa la componente de f_PWM; un amplificador no inversor de ganancia G = 1 + R_f/R_g lleva el resultado a la escala de AI1:'),
  EQ('V_AI1 = (1 + R_f/R_g)·D·V_H = 10·D  [V]', 3),
  H2('D', 'Optoacopladores y relación de transferencia'),
  P('Un optoacoplador transfiere una señal por luz entre dos circuitos sin conexión eléctrica. En el PC817 la corriente de colector disponible es I_C = CTR·I_F, donde la relación de transferencia CTR va de 50 % a 600 % según la clasificación y varía con la temperatura [8]. Por esa dispersión el PC817 sirve para señales todo o nada, pero no para transmitir una tensión analógica; y por su lentitud (decenas de microsegundos) tampoco para el PWM de 20 kHz, que usa el 6N137, de salida lógica y 10 Mbit/s [4].'),
  H2('E', 'Protocolo MQTT'),
  P('MQTT es un protocolo de publicación y suscripción sobre TCP [10]. Los clientes publican mensajes en tópicos jerárquicos de un servidor intermediario (broker) y reciben los de los tópicos a los que se suscriben. Ofrece mensajes retenidos, que el broker entrega a quien se suscribe después, y un mensaje de “última voluntad” que el broker publica si un cliente se desconecta sin avisar; ambos se usan aquí para el estado del equipo y la detección de pérdida del ESP32.'),

  H1('Diseño del hardware'),
  H2('A', 'Arquitectura y dominios de tierra'),
  P('El sistema tiene tres dominios (Fig. 1). El del ESP32 se alimenta con una fuente propia de 5 V por el pin VIN (bornera J11) y también alimenta el ACS712, cuya salida va al ADC. El dominio analógico del V20 usa una fuente externa de 5 V (6N137 y 74HC14) y 12 V (LM358), cuyo negativo se une al borne 92 (0V analógico). Las entradas y salidas digitales usan la salida de 24 V del propio variador (bornes 100 y 101). Ninguna conexión une la tierra del ESP32 con el 0V del V20: si el ESP32 tomara sus 5 V de la fuente del V20, su tierra quedaría unida al borne 92 y los optoacopladores dejarían de aislar.'),
  H2('B', 'Acondicionador de consigna'),
  P('El GPIO 25 genera el PWM de 20 kHz y 10 bits. El LED del 6N137 se excita a través de 220 Ω; con V_F entre 1,38 y 1,70 V la corriente queda entre 7,3 y 8,7 mA, por encima del umbral máximo de 5 mA [4]. La salida de colector abierto lleva un pull-up de 1 kΩ, con el desacople de 100 nF entre los pines 8 y 5 que exige la hoja de datos. El 74HC14, alimentado a 5 V, restaura los flancos y fija V_H = 5 V; como el opto y el inversor invierten cada uno la señal, la cadena conserva la polaridad. Con el ESP32 en reset el LED queda apagado y AI1 en 0 V: la falla conduce a 0 Hz. Las entradas libres del 74HC14 se fijan (3 y 5 a 0V; 9, 11 y 13 a 5 V) y la unidad B del LM358 queda como seguidor con la entrada a 0V, para que no oscilen.'),
  H2('C', 'Ecuaciones de diseño'),
  P('Con R = R_f = R_g = 10 kΩ y C = 1 µF:'),
  EQ('f_c = 1/(2π·R·C) = 15,9 Hz', 4),
  EQ('ΔV_pp = G·V_H·D(1 − D)/(R·C·f_PWM)', 5),
  EQ('ΔV_min = 10 V/(2ᴺ − 1) = 9,8 mV', 6),
  P('El rizado (5) es máximo en D = 0,5: 12,5 mVpp en AI1, equivalentes a 0,075 Hz. La solución exacta por tramos exponenciales difiere de la aproximación lineal en menos de 0,01 % porque RC = 200·T (Fig. 2). El tiempo de establecimiento es t_s ≈ 5RC = 50 ms (Tabla I).'),
  ...tcap('I', 'Valores de diseño del acondicionador'),
  table([
    ['Magnitud', 'Diseño', 'Equivalente'],
    ['Escala', '10·D V', '60·D Hz'],
    ['f_c del filtro', '15,9 Hz', '−62 dB a 20 kHz'],
    ['Rizado máx. (D = 0,5)', '12,5 mVpp', '0,075 Hz'],
    ['Resolución (10 bits)', '9,8 mV', '0,059 Hz'],
    ['Establecimiento', '50 ms', '5τ'],
    ['Consumo fuente 5 V', '≈ 20 mA', '6N137 + pull-up'],
    ['Consumo fuente 12 V', '≈ 2 mA', 'LM358 + carga'],
  ], [2100, 1485, 1485]),
  img('slide_rizado_vs_D.png', 330, 183),
  cap('Fig. 2. Rizado en AI1 frente al ciclo de trabajo: solución exacta y aproximación lineal.'),
  H2('D', 'Protecciones, alimentación y tolerancias'),
  P('Con 12 V de alimentación la salida del LM358 llega a unos 10,5 V, apenas 0,5 V por encima del fondo de escala; por eso se recomienda 15 V y se verifica en banco que V(60 Hz) − V(55 Hz) ≈ 0,83 V, señal de que no hay recorte. El Zener 1N4742A de 12 V tras 100 Ω limita AI1 si la realimentación se abre con 15 V. La impedancia de AI1 es mayor que 30 kΩ, de modo que los 100 Ω introducen un error menor que 0,33 %. Con la fuente de 5 V al ±5 % y resistencias de ganancia al 1 %, el fondo de escala queda entre 9,41 y 10,61 V; sumado a la precisión de ±5 % de AI1 [3], el error podría llegar a ±6 %, y por eso el escalado se calibra en el variador: con la consigna de 60 Hz se escribe r0752 en P0759[0].'),
  H2('E', 'Interfaz de mando y estado'),
  P('El 6N137 no puede manejar las entradas digitales, porque su salida soporta como máximo 7 V y el V20 trabaja con 24 V. Se usaron tres PC817 con el colector en el borne 100 (24 V) y el emisor en DI1, DI2 y DI3, con las entradas en modo PNP (DIC al borne 101). Cada LED lleva 220 Ω desde su GPIO y 10 kΩ a tierra para que permanezca apagado durante el arranque del ESP32. El estado “en marcha” (DO1, transistor libre de potencial) se lee con un cuarto PC817 cuyo LED se alimenta desde 24 V por 2,2 kΩ; su transistor lleva a tierra el GPIO 35, que tiene un pull-up externo de 10 kΩ. La falla (DO2) es el contacto seco de un relé interno, aislado 4 kV, y se lee directamente en el GPIO 33 con pull-up interno y 1 kΩ en serie. No se usaron los relés de estado sólido del laboratorio anterior porque su salida es un triac, inadecuado para 24 V de continua. La Tabla II resume los cálculos.'),
  ...tcap('II', 'Interfaz digital ESP32 – V20'),
  table([
    ['Señal', 'Elemento', 'Cálculo'],
    ['DI1/DI2/DI3', 'PC817 + 220 Ω', 'I_F = 9,5 mA; I_C ≥ 4,8 mA (CTR ≥ 50 %)'],
    ['DO1 → GPIO35', 'PC817 + 2,2 kΩ', 'I_F ≈ 10 mA; P_R = 0,23 W'],
    ['DO2 → GPIO33', 'contacto seco', 'pull-up interno; 1 kΩ serie'],
    ['24 V del V20', 'bornes 100–101', '≤ 40 mA peor caso (máx. 50 mA)'],
  ], [1250, 1300, 2520]),
  P([t('Las entradas del V20 consumen como máximo 15 mA [9], pero el catálogo no da el valor típico; con I_C mínimo de 4,8 mA el margen depende de la CTR real del PC817. Por eso la prueba de banco exige al menos 20 V entre DI y 0V con la orden activa; si no se cumple, se baja la resistencia a 150 Ω o se usa un PC817 de clase C (CTR 200–400 %). Tensión medida: '), PEND(), t(' V.')]),
  H2('F', 'Medición de corriente'),
  P('Un ACS712 (efecto Hall, aislado de la fase) se intercala entre el borne 83 (salida U del V20) y el borne 1 del motor. Su salida se reduce de 5 V a 3,3 V con un divisor de 10 kΩ y 20 kΩ; un condensador de 22 nF forma con la resistencia equivalente de 6,7 kΩ un filtro de 1,08 kHz que elimina la portadora de conmutación del variador. El firmware calcula el valor eficaz como la desviación estándar de la señal, I_rms = √(⟨v²⟩ − ⟨v⟩²)/S, con lo que un desplazamiento de continua no se interpreta como corriente; además resta el ruido medido en vacío y verifica que la media esté entre 2,2 y 2,8 V para detectar el sensor desconectado. La ventana de medida se adapta a la frecuencia: clamp(5000/f, 400, 2000) ms.'),
  H2('G', 'Tarjeta impresa'),
  P('El circuito se llevó a una tarjeta de una cara de 142,2 × 86,4 mm, apta para fabricación por planchado (Fig. 3). El ESP32 DevKit de 30 pines se monta en tiras hembra, con dos posiciones para la fila opuesta porque la separación entre filas varía entre fabricantes (22,86 o 25,40 mm). Las pistas son de 0,8 mm (señal) y 1,0 mm (alimentación), con holgura mínima de 0,505 mm; tres puentes de alambre evitan una segunda capa. La barrera de aislamiento atraviesa los optoacopladores y ninguna pista la cruza. Los archivos Gerber se verificaron con un programa independiente que los rasteriza y compara las islas de cobre con la lista de conexiones: 32 redes, 0 cortos y 0 aberturas. La corriente del motor no pasa por la tarjeta.'),
  img('pcb_montaje.png', 330, 202),
  cap('Fig. 3. Mapa de montaje de la tarjeta (lado de componentes). En rojo, los puentes de alambre W1–W3; línea de puntos, barrera de aislamiento.'),

  H1('Firmware y aplicación'),
  H2('A', 'Firmware de la guía'),
  P('consigna_pwm_v20.ino (versión 2.0, basada en el de la guía) fija D = f/60 con el periférico LEDC y recibe por monitor serie una frecuencia de 0 a 60 Hz, el perfil de escalones 0–15–30–45–60–30–0 Hz y la parada. Se añadió compatibilidad con los núcleos 2.x y 3.x, perfil no bloqueante y marca de tiempo en cada cambio.'),
  H2('B', 'Firmware IoT (v3.2)'),
  P('v20_iot_esp32.ino implementa una máquina de estados DETENIDO, MARCHA y FALLO. Al energizarse arranca en FALLO con la causa RETORNO_ALIMENTACION, de modo que el motor nunca arranca solo tras un corte: hace falta un RESET, que además envía un pulso de 300 ms por DI3. El sentido solo puede cambiarse con el motor detenido, y las órdenes retenidas en el broker se ignoran durante 1,5 s después de reconectar para que un START antiguo no arranque el motor. La Tabla III resume las protecciones; todas abren DI1, llevan AI1 a 0 V y publican la causa.'),
  ...tcap('III', 'Protecciones del firmware'),
  table([
    ['Falla', 'Condición', 'Tiempo'],
    ['Falla del V20', 'DO2 cerrado', 'inmediato'],
    ['V20 sin marcha', 'DI1 activo y DO1 abierto', '2 s'],
    ['Pérdida de fase', 'f > 5 Hz e I < máx(0,35 A; 0,15·Iₙ)', '2 s'],
    ['Sobrecorriente', 'I > 2,5·Iₙ', '0,5 s'],
    ['Sobrecarga I²t', 'θ ≥ 1,2 (τ = 300 s)', 'según carga'],
    ['Falla del sensor', 'media fuera de 2,2–2,8 V', 'inmediato'],
    ['Pérdida de red', 'marcha remota sin MQTT', '10 s'],
  ], [1300, 2470, 1300]),
  H2('C', 'Comunicación'),
  P('El ESP32 se conecta a un broker HiveMQ Cloud por TLS (puerto 8883) y la aplicación por WebSocket seguro (8884). Los tópicos, bajo el prefijo del grupo, son: cmd (START, STOP, EMERGENCY, RESET, FWD, REV, perfil, calibración), consigna, config (rampa, Iₙ, f_mín, f_máx, vigilancia), estado y alarma (retenidos), aviso, telemetria (JSON de 26 campos cada 1 s) y online, que es el mensaje de última voluntad. Las credenciales están en un archivo credenciales.h que no se sube al repositorio.'),
  H2('D', 'Aplicación móvil'),
  P('La aplicación es una página web sin dependencias con un cliente MQTT 3.1.1 propio sobre WebSocket; funciona en el navegador del celular y se publica con GitHub Pages. Muestra frecuencia, corriente, consigna, velocidad síncrona, el estado de DI1, DO1, DO2 y del sensor, una tendencia de 120 s y un registro de eventos; permite marcha, paro, emergencia, reset, sentido, consigna de 0 a 60 Hz, perfil y configuración (Fig. 4).'),
  img('app_marcha.png', 190, 254),
  cap('Fig. 4. Aplicación en el celular durante una marcha a 30 Hz (simulación).'),

  H1('Verificación por simulación'),
  P('Antes de conectar el variador, el firmware real se compiló para el computador con encabezados que reemplazan las funciones de Arduino. Sus entradas y salidas se conectaron a un modelo del V20 (rampas P1120/P1121, DI1–DI3, DO1, DO2 y AI1 calibrada) y del motor (corriente de magnetización de 1,4 A más un término proporcional a la aceleración y a la carga), medido por un ACS712 simulado con ruido y portadora. Un broker MQTT y un navegador automatizado manejaron la aplicación como lo haría un usuario. Para acortar el ensayo la constante térmica se redujo a 30 s. Se superaron 30 de 30 pruebas (Tabla IV, Fig. 5).'),
  ...tcap('IV', 'Pruebas seleccionadas de la simulación'),
  table([
    ['Prueba', 'Resultado'],
    ['Consigna 30 Hz → AI1', '5,005 V'],
    ['Rampa 0 → 30 Hz (P1120 = 10 s)', '4,96 s (teórico 5,00 s)'],
    ['Corriente medida vs. real a 30 Hz', '1,400 A vs. 1,400 A'],
    ['Paro de 60 Hz a 0 Hz', '10,4 s'],
    ['Inversión con el motor en marcha', 'rechazada'],
    ['Falla del V20 (DO2) y reset por DI3', 'FALLO → DETENIDO'],
    ['Corte de energía del V20', 'FALLO a los 2,5 s'],
    ['Fase abierta', 'FALLO a los 3,0 s'],
    ['Sobrecorriente (2,6 A > 2,5 A)', 'disparo en 0,9 s'],
    ['Sobrecarga de 1,4·Iₙ (τ = 30 s)', 'disparo I²t a los 16 s'],
    ['Pérdida de red en marcha', 'DI1 abierto a los 10,1 s'],
    ['Emergencia desde la app', 'DI1 abierto en 40 ms'],
    ['ACS712 desconectado', 'FALLO y marcha bloqueada'],
  ], [2900, 2170]),
  img('sim_iot.png', 330, 225),
  cap('Fig. 5. Simulación completa: frecuencia del V20 y consigna, corriente real y medida, y estado del firmware. Las líneas verticales marcan las fallas provocadas.'),

  H1('Procedimiento experimental'),
  bullet('Verificación de la tarjeta sin variador: continuidad abierta entre la tierra del ESP32 (J11) y el borne 92; 5 V y 12 V en los integrados; consigna de 0, 30 y 60 Hz y rizado con D = 0,5 en acople AC.'),
  bullet('Conexión a los bornes 89, 92, 95–97, 100, 102, 105 y 106 con el breaker en OFF; puentes 99–101 y 103–101 en el banco.'),
  bullet('Parte de la guía: puesta en marcha rápida (P0304–P0311), P0700 = 1, P1000 = 2 y AI1 con P0756 = 0, P0757 = 0 V, P0758 = 0 %, P0760 = 100 %, P2000 = 60 Hz; calibración P0759[0] = r0752 a 60 Hz.'),
  bullet('Ensayos de la guía: linealidad, rampas P1120 = 5, 10 y 20 s, límites P1080 = 15 Hz y P1082 = 45 Hz, característica V/f con P1300 = 0, 2 y P1310 aumentado, perfil de escalones.'),
  bullet('Modo IoT: P0700 = 2, P0701 = 1, P0702 = 12, P0703 = 9, P0731 = 52.2, P0732 = 52.3. Pruebas desde la app: reset inicial, marcha, paro, sentido, emergencia, falla provocada y comparación de la corriente con r0027 a 15, 30, 45 y 60 Hz.'),
  bullet('Cierre: motor detenido, breaker en OFF y restablecimiento con P0003 = 1, P0010 = 30 y P0970 = 21.'),

  H1('Resultados'),
  H2('A', 'Verificación del acondicionador'),
  ...tcap('V', 'Verificación en banco'),
  table([
    ['Medición', 'Diseño', 'Medido', 'Error'],
    ['+5 V = V_H', '5,00 V', [PEND()], [PEND()]],
    ['+12 V (LM358)', '12,0 V', [PEND()], [PEND()]],
    ['AI1 con 0 Hz', '0,00 V', [PEND()], '—'],
    ['AI1 con 30 Hz', '5,00 V', [PEND()], [PEND()]],
    ['AI1 con 60 Hz', '10,00 V', [PEND()], [PEND()]],
    ['V(60) − V(55)', '0,83 V', [PEND()], [PEND()]],
    ['Rizado D = 0,5', '12,5 mVpp', [PEND()], [PEND()]],
    ['GND ESP32 – 0V', 'abierto', [PEND()], '—'],
  ], [1770, 1100, 1100, 1100]),
  H2('B', 'Calibración y linealidad'),
  P([t('Con la consigna de 60 Hz, r0752 = '), PEND(), t(' V; se ajustó P0759[0] a ese valor. Con 30 Hz, r0021 = '), PEND(), t(' Hz.')]),
  ...tcap('VI', 'Linealidad de la consigna (P0759 calibrado)'),
  table([
    ['Consigna [Hz]', 'V mult. [V]', 'r0752 [V]', 'r0021 [Hz]', 'n [rpm]', 's [%]'],
    ['0', [PEND()], [PEND()], [PEND()], [PEND()], '—'],
    ['15', [PEND()], [PEND()], [PEND()], [PEND()], [PEND()]],
    ['30', [PEND()], [PEND()], [PEND()], [PEND()], [PEND()]],
    ['45', [PEND()], [PEND()], [PEND()], [PEND()], [PEND()]],
    ['60', [PEND()], [PEND()], [PEND()], [PEND()], [PEND()]],
  ], [870, 840, 840, 840, 840, 840], { centerFirst: true }),
  H2('C', 'Rampas de aceleración'),
  ...tcap('VII', 'Efecto de la rampa de aceleración (0 → 60 Hz)'),
  table([
    ['P1120 [s]', 'dω/dt [rad/s²]', 'Tiempo medido [s]', 'I máx. [A]'],
    ['5', '75,4', [PEND()], [PEND()]],
    ['10', '37,7', [PEND()], [PEND()]],
    ['20', '18,8', [PEND()], [PEND()]],
  ], [1000, 1300, 1470, 1300], { centerFirst: true }),
  H2('D', 'Límites de frecuencia'),
  P([t('Con P1080 = 15 Hz y P1082 = 45 Hz, r0021 se mantuvo en '), PEND(), t(' Hz para consignas de 0 a 15 Hz y en '), PEND(), t(' Hz para consignas de 45 a 60 Hz.')]),
  H2('E', 'Característica V/f'),
  ...tcap('VIII', 'Tensión de salida r0025 [V] según la característica V/f'),
  table([
    ['f [Hz]', 'Teórica lineal', 'Lineal', 'Cuadrática', 'Lineal + boost'],
    ['10', '36,7', [PEND()], [PEND()], [PEND()]],
    ['20', '73,3', [PEND()], [PEND()], [PEND()]],
    ['30', '110,0', [PEND()], [PEND()], [PEND()]],
    ['40', '146,7', [PEND()], [PEND()], [PEND()]],
    ['50', '183,3', [PEND()], [PEND()], [PEND()]],
    ['60', '220,0', [PEND()], [PEND()], [PEND()]],
  ], [800, 1070, 1000, 1100, 1100], { centerFirst: true }),
  H2('F', 'Mando y supervisión desde la aplicación'),
  ...tcap('IX', 'Pruebas en banco del modo IoT'),
  table([
    ['Prueba', 'Esperado', 'Medido'],
    ['V(95–101) con MARCHA', '≥ 20 V', [PEND()]],
    ['V(95–101) con PARO', '0 V', [PEND()]],
    ['GPIO35 en marcha / parado', '< 0,5 V / 3,3 V', [PEND()]],
    ['I app vs. r0027 a 30 Hz', 'error < 10 %', [PEND()]],
    ['I app vs. r0027 a 60 Hz', 'error < 10 %', [PEND()]],
    ['Emergencia → inicio de desaceleración', '< 0,5 s', [PEND()]],
    ['Sentido con el motor en marcha', 'rechazado', [PEND()]],
  ], [2300, 1385, 1385]),
  P([ph('[Fig. 6: r0021 vs. consigna antes y después de calibrar; Fig. 7: curvas V/f medidas. Se generan con analisis_resultados.py.]')], { noIndent: true }),

  H1('Análisis y cuestionario técnico'),
  H2('A', 'Error de consigna antes y después de calibrar'),
  P([t('El error respecto al fondo de escala es e = (r0021 − f_cons)/60 × 100 %. Antes de calibrar el error máximo fue '), PEND(), t(' %, consistente con un fondo de escala de '), PEND(), t(' V; después de ajustar P0759 fue '), PEND(), t(' %. El residuo se atribuye al offset del LM358, a la distorsión de ancho de pulso del 6N137 y a la cuantización de 10 bits de AI1.')]),
  H2('B', 'Curvas V/f a baja frecuencia'),
  P('A baja frecuencia la caída R_s·I es comparable con la tensión aplicada, de modo que con la ley lineal pura el flujo y el par caen. El refuerzo P1310 suma un término casi constante que eleva la curva a bajas frecuencias y converge con la lineal cerca de fₙ. La característica cuadrática queda por debajo de la recta en el rango intermedio porque reduce el flujo cuando el par de carga esperado es bajo.'),
  P([ph('[Comparar con los valores medidos de la Tabla VIII.]')], { noIndent: true }),
  H2('C', 'Tiempo de rampa y corriente máxima'),
  P('La ecuación de movimiento es J·dω/dt = T_e − T_L − B·ω. En vacío T_e ≈ J·dω/dt + B·ω; una rampa de 0 a 3600 rpm en t_r impone dω/dt = 377/t_r: 75,4, 37,7 y 18,8 rad/s² para 5, 10 y 20 s. La corriente es la magnetizante, casi constante a V/f constante, más la productora de par, proporcional a T_e; por eso I_máx crece al acortar la rampa. La simulación lo reproduce: la corriente sube de 1,40 A a 1,67 A durante la aceleración y vuelve al valor de vacío.'),
  P([t('Medido en banco: '), PEND(), t(' A, '), PEND(), t(' A y '), PEND(), t(' A.')]),
  H2('D', 'Constante de tiempo del filtro'),
  P('Con τ = 10 ms la consigna se establece en ≈ 50 ms, doscientas veces menos que la rampa de 10 s, de modo que la dinámica del filtro es invisible para el motor. Con τ = 1 s el establecimiento tomaría ≈ 5 s, se sumaría a la rampa y deformaría el perfil, aunque el rizado bajaría a 0,13 mVpp, mejora innecesaria porque ya es inferior a la resolución.'),
  H2('E', 'Aislar el PWM y no la señal analógica'),
  P('La CTR de un optoacoplador es alineal y varía con la temperatura y el envejecimiento; una señal analógica aislada directamente arrastraría esos errores. Un PWM solo necesita que el opto reproduzca los flancos: la información está en el tiempo, no en la amplitud, y la amplitud se fija de nuevo del lado del V20 con el 74HC14. El mismo argumento explica por qué los PC817 son adecuados para las órdenes todo o nada.'),
  H2('F', 'Resolución con 8 bits'),
  P('Con N = 8, ΔV = 10 V/255 = 39,2 mV, es decir 0,235 Hz por paso, frente a 0,059 Hz con 10 bits. Como AI1 también tiene 10 bits, aumentar la resolución del PWM por encima de 10 bits no mejora la consigna efectiva.'),
  H2('G', 'Característica cuadrática'),
  P('Conviene para ventiladores y bombas centrífugas, cuyo par crece con el cuadrado de la velocidad: reduce la tensión, el flujo y las pérdidas en el hierro. Con carga de par constante el flujo reducido no alcanza para el par requerido a baja velocidad: el deslizamiento y la corriente aumentan, el motor puede calarse y el variador puede disparar por sobrecorriente.'),
  H2('H', 'Refuerzo de tensión excesivo'),
  P('Un refuerzo mayor que el necesario sobreexcita el núcleo a baja frecuencia: la corriente magnetizante crece por saturación y con ella las pérdidas en el cobre y en el hierro. Como el motor es autoventilado y gira lento, se calienta aun sin carga, y puede actuar la protección de sobrecorriente.'),
  H2('I', 'Seguridad del mando remoto'),
  P('Un mando por red debe fallar hacia el estado seguro. Por eso las órdenes van a entradas que solo se activan con corriente por el LED: un ESP32 apagado, reiniciado o desconectado deja DI1 abierta y AI1 en 0 V. El firmware añade el bloqueo tras un corte de energía, la parada por pérdida de comunicación y la comprobación cruzada entre la orden (DI1) y la respuesta del variador (DO1). La limitación que queda es que DO2 se lee por un contacto normalmente abierto: un cable suelto se interpreta como “sin falla”; usar el contacto normalmente cerrado (borne 104) lo haría a prueba de rotura del cable.'),

  H1('Conclusiones'),
  P('La simulación del firmware real frente a un modelo del variador y del motor verificó las 30 funciones previstas antes de energizar el banco, entre ellas las rampas (4,96 s frente a 5,00 s), la medición de corriente y las siete protecciones, con una parada de emergencia de 40 ms desde la aplicación.'),
  P('El reemplazo de los relés por optoacopladores PC817 redujo el tamaño y el consumo de la interfaz y mantuvo el aislamiento; la tarjeta de una cara conserva una barrera que ninguna pista cruza y se verificó sin cortos ni aberturas desde los propios archivos de fabricación.'),
  P([ph('[Completar con los datos de banco: (1) escala 0–10 V y rizado medido __ mVpp frente a 12,5 mVpp; (2) aislamiento verificado sin continuidad; (3) error de __ % a __ % tras calibrar P0759; (4) efecto observado de rampas, límites y V/f; (5) corriente de la app frente a r0027 con error de __ %.]')], { noIndent: true }),

  H1('Referencias'),
];
const refs = [
  'N. Mohan, T. M. Undeland y W. P. Robbins, Power Electronics: Converters, Applications, and Design, 3rd ed. Hoboken, NJ, USA: Wiley, 2003.',
  'J. Fraile Mora, Máquinas Eléctricas, 6.ª ed. Madrid, España: McGraw-Hill, 2008.',
  'Siemens AG, “SINAMICS V20 Inverter — Operating Instructions,” Nanjing, China. [En línea]. Disponible: https://support.industry.siemens.com',
  '“6N137 High Speed 10 MBit/s Logic Gate Optocoupler,” hoja de datos.',
  'Texas Instruments, “LMx58-N Low-Power, Dual-Operational Amplifiers,” hoja de datos.',
  'Espressif Systems, “LED Control (LEDC),” ESP32 Arduino Core Documentation. [En línea]. Disponible: https://docs.espressif.com/projects/arduino-esp32',
  'J. D. Guillot Fula, “Guía de Laboratorio N.º 2 — Control de velocidad con V20,” Universidad del Magdalena, Santa Marta, 2026.',
  'Sharp, “PC817 Series — High Density Mounting Type Photocoupler,” hoja de datos.',
  'Siemens AG, “SINAMICS V20 basic converters,” Catálogo D 31.1, 2018, cap. 7.',
  'OASIS, “MQTT Version 3.1.1,” OASIS Standard, 2014.',
  'Allegro MicroSystems, “ACS712 Fully Integrated, Hall-Effect-Based Linear Current Sensor IC,” hoja de datos.',
];
refs.forEach((r, i) => cuerpo.push(new Paragraph({ children: [t(`[${i + 1}] `, { size: 16 }), t(r, { size: 16 })], indent: { left: 360, hanging: 360 }, spacing: { after: 40 }, alignment: AlignmentType.LEFT })));

const margins = { top: 1080, bottom: 1080, left: 893, right: 893 };
const doc = new Document({
  creator: 'Grupo', title: 'Informe Laboratorio 2 — V20 con ESP32 e IoT',
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  numbering: { config: [{ reference: 'vin', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 280, hanging: 200 } } } }] }] },
  sections: [
    { properties: { page: { size: { width: 12240, height: 15840 }, margin: margins } }, children: cab },
    { properties: { type: SectionType.CONTINUOUS, page: { size: { width: 12240, height: 15840 }, margin: margins }, column: { count: 2, space: 300 } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 })] })] }) },
      children: cuerpo },
  ],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(path.join(__dirname, 'Informe_Lab2_V20_ESP32_IoT_BORRADOR.docx'), b); console.log('ok'); });
