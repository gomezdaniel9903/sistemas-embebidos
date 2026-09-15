"""
Conducir el mBot2 desde el teclado + CSV + CONTROL DE VELOCIDAD y LED por color.

Novedades respecto a la version anterior:
  - Teclas + / -  suben y bajan la velocidad (tambien vale = para subir, por si
    tu teclado necesita Shift para el +).
  - El LED del CyberPi cambia de color segun el rango de velocidad:
        lento  (<=33)  -> verde
        medio  (<=66)  -> ambar
        rapido (>66)   -> rojo
  - El CSV ahora tambien guarda la velocidad de cada instante.

Requisitos (una sola vez):
    pip install -e .        # dentro de la carpeta del repo mbot_python
    pip install pynput

Uso:
    - Enciende el mBot2 (que NO este conectado a mBlock ni al movil).
    - Ejecuta:  python conducir_mbot2_csv_velocidad_led.py
    - Flechas para conducir, + / - para la velocidad, ESC para salir.
"""

import time
import csv
from datetime import datetime
from mbot2 import MBot2
from pynput import keyboard

# ---- Ajustes ----
# --- Notas naturales (frecuencia en Hz) ---
NOTAS = {
    "SOL4": 392, "LA4": 440, "SI4": 494,
    "DO5": 523, "RE5": 587, "MI5": 659, "FA5": 698, "SOL5": 784,
}

# Melodia de "Cumpleanos feliz": (nota, duracion en tiempos)
CUMPLEANOS = [
    ("SOL4", 0.5), ("SOL4", 0.5), ("LA4", 1), ("SOL4", 1), ("DO5", 1), ("SI4", 1.5),
    ("SOL4", 0.5), ("SOL4", 0.5), ("LA4", 1), ("SOL4", 1), ("RE5", 1), ("DO5", 1.5),
    ("SOL4", 0.5), ("SOL4", 0.5), ("SOL5", 1), ("MI5", 1), ("DO5", 1), ("SI4", 1), ("LA4", 1.5),
    ("FA5", 0.5), ("FA5", 0.5), ("MI5", 1), ("DO5", 1), ("RE5", 1), ("DO5", 1.5),
]

TIEMPO = 0.4   # segundos por tiempo (sube el numero para ir mas lento)

def tocar_cumpleanos(bot):
    bot.volume(80)                          # opcional
    for nota, tiempos in CUMPLEANOS:
        dur = tiempos * TIEMPO
        bot.beep(NOTAS[nota], dur * 0.85)   # el tono suena el 85% del hueco
        time.sleep(dur)                     # la pausa marca el ritmo
VELOCIDAD = 50        # velocidad inicial (0-100)
PASO = 10             # cuanto sube/baja con + / -
VEL_MIN = 10
VEL_MAX = 100
UMBRAL = 10           # cm: por debajo, se bloquea SOLO el avance
INTERVALO_LOG = 0.5   # segundos entre filas del CSV

# ---- Estado de las teclas (se actualiza en segundo plano) ----
pulsadas = set()

def al_pulsar(tecla):
    global VELOCIDAD
    pulsadas.add(tecla)

    # Ajuste de velocidad con + / - (los simbolos vienen en tecla.char;
    # las flechas son objetos sin .char, por eso el try/except)
    try:
        c = tecla.char
    except AttributeError:
        c = None
    if c in ("+", "="):
        VELOCIDAD = min(VEL_MAX, VELOCIDAD + PASO)
    elif c in ("-", "_"):
        VELOCIDAD = max(VEL_MIN, VELOCIDAD - PASO)

    if tecla == keyboard.Key.esc:
        return False        # detiene el listener y salimos

def al_soltar(tecla):
    pulsadas.discard(tecla)

# ---- Color del LED segun el rango de velocidad ----
def color_por_velocidad(v):
    if v <= 33:
        return (0, 255, 0)      # verde  -> lento
    elif v <= 66:
        return (255, 150, 0)    # ambar  -> medio
    else:
        return (255, 0, 0)      # rojo   -> rapido

# ---- Conexion ----
print("Conectando con el mBot2 por Bluetooth...")
bot = MBot2()               # busca y conecta automaticamente
print("Conectado. Flechas = conducir | +/- = velocidad | ESC = salir.")

listener = keyboard.Listener(on_press=al_pulsar, on_release=al_soltar)
listener.start()

# ---- Preparar el archivo CSV ----
nombre_csv = "datos_mbot2_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
archivo_csv = open(nombre_csv, "w", newline="", encoding="utf-8")
escritor = csv.writer(archivo_csv)
escritor.writerow(["tiempo_s", "distancia_cm", "velocidad", "bateria", "luz", "sonido", "accion"])
print("Guardando datos en:", nombre_csv)

ultima_accion = None        # ultimo comando de movimiento enviado
ultima_velocidad = None     # ultima velocidad enviada al motor
ultimo_color = None         # ultimo color enviado al LED
inicio = time.time()
ultimo_log = inicio

try:
    while listener.running:
        
        distancia = bot.distance()      # ultrasonico, en cm (cada vuelta)

        # 1) Decidir la accion segun las teclas + freno de seguridad
        if keyboard.Key.up in pulsadas and distancia > UMBRAL:
            accion = "adelante"
        elif keyboard.Key.down in pulsadas:
            accion = "atras"
        elif keyboard.Key.left in pulsadas:
            accion = "izquierda"
        elif keyboard.Key.right in pulsadas:
            accion = "derecha"
        else:
            accion = "parar"

        # 2) Enviar la orden si cambio la accion O si cambio la velocidad
        #    mientras seguimos en movimiento (para que el + / - se note al vuelo)
        if accion != ultima_accion or (accion != "parar" and VELOCIDAD != ultima_velocidad):
            if accion == "adelante":
                bot.forward(VELOCIDAD)     # sin segundos -> continuo
            elif accion == "atras":
                bot.backward(VELOCIDAD)
            elif accion == "izquierda":
                bot.turn_left(VELOCIDAD)
            elif accion == "derecha":
                bot.turn_right(VELOCIDAD)
            else:
                bot.stop()
            ultima_accion = accion
            ultima_velocidad = VELOCIDAD

        # 3) LED por rango de velocidad (solo cuando cambia de color)
        color = color_por_velocidad(VELOCIDAD)
        if color != ultimo_color:
            bot.led(*color)                # equivale a bot.led(r, g, b)
            ultimo_color = color

        # 4) Registro periodico en el CSV (no en cada vuelta)
        ahora = time.time()
        if ahora - ultimo_log >= INTERVALO_LOG:
            bateria = bot.battery()
            luz = bot.brightness()
            sonido = bot.loudness()
            escritor.writerow([
                round(ahora - inicio, 2),
                round(distancia, 1),
                VELOCIDAD,
                bateria,
                luz,
                sonido,
                accion,
            ])
            archivo_csv.flush()
            ultimo_log = ahora

        # Lectura en vivo en la terminal
        print(f"Dist: {distancia:5.1f} cm | Vel: {VELOCIDAD:3d} | {accion:10s}", end="\r")

        time.sleep(0.05)

finally:
    # Salir de forma limpia pase lo que pase
    
    bot.stop()
    bot.led_off()
    time.sleep(0.5)
    bot.run('cyberpi.audio.play("Bye")')
    time.sleep(0.5)
    tocar_cumpleanos(bot)
    bot.disconnect()
    archivo_csv.close()
    print("\nDesconectado. Datos guardados en:", nombre_csv)
