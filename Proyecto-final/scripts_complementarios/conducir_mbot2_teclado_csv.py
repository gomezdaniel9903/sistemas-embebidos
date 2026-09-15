"""
Conducir el mBot2 desde el teclado + REGISTRAR DATOS EN CSV (Opcion B).

Corre en tu PC. Conduces con las flechas (igual que antes) y, mientras tanto,
el script guarda en un archivo .csv la distancia, la bateria, la luz y el sonido
con marca de tiempo, para analizarlo o graficarlo despues.

Requisitos (una sola vez):
    pip install -e .        # dentro de la carpeta del repo mbot_python
    pip install pynput

Uso:
    - Enciende el mBot2 (que NO este conectado a mBlock ni al movil).
    - Ejecuta:  python conducir_mbot2_teclado_csv.py
    - Flechas para conducir. ESC para salir.
    - Al terminar, tendras un archivo datos_mbot2_AAAAMMDD_HHMMSS.csv
      en la misma carpeta desde donde lanzaste el script.
"""

import time
import csv
from datetime import datetime
from mbot2 import MBot2
from pynput import keyboard

# ---- Ajustes ----
VELOCIDAD = 50        # 0-100
UMBRAL = 10           # cm: por debajo, se bloquea SOLO el avance
INTERVALO_LOG = 0.5   # segundos entre filas del CSV (subelo si quieres menos datos)

# ---- Estado de las teclas (se actualiza en segundo plano) ----
pulsadas = set()

def al_pulsar(tecla):
    pulsadas.add(tecla)
    if tecla == keyboard.Key.esc:
        return False        # devuelve False -> detiene el listener y salimos

def al_soltar(tecla):
    pulsadas.discard(tecla)

# ---- Conexion ----
print("Conectando con el mBot2 por Bluetooth...")
bot = MBot2()               # busca y conecta automaticamente
print("Conectado. Flechas para conducir, ESC para salir.")

listener = keyboard.Listener(on_press=al_pulsar, on_release=al_soltar)
listener.start()

# ---- Preparar el archivo CSV ----
nombre_csv = "datos_mbot2_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
archivo_csv = open(nombre_csv, "w", newline="", encoding="utf-8")
escritor = csv.writer(archivo_csv)
escritor.writerow(["tiempo_s", "distancia_cm", "bateria", "luz", "sonido", "accion"])
print("Guardando datos en:", nombre_csv)

ultima_accion = None        # para no reenviar el mismo comando una y otra vez
inicio = time.time()
ultimo_log = inicio

try:
    while listener.running:
        distancia = bot.distance()      # lectura del ultrasonico, en cm (cada vuelta)

        # Decidir la accion segun las teclas + freno de seguridad.
        # El "distancia > UMBRAL" solo afecta al AVANCE: puedes retroceder y girar
        # aunque tengas un obstaculo delante.
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

        # Enviar la orden SOLO cuando cambia (no saturar el Bluetooth)
        if accion != ultima_accion:
            if accion == "adelante":
                bot.forward(VELOCIDAD)     # sin segundos -> movimiento continuo
            elif accion == "atras":
                bot.backward(VELOCIDAD)
            elif accion == "izquierda":
                bot.turn_left(VELOCIDAD)
            elif accion == "derecha":
                bot.turn_right(VELOCIDAD)
            else:
                bot.stop()
            ultima_accion = accion

        # ---- Registro periodico en el CSV (no en cada vuelta) ----
        ahora = time.time()
        if ahora - ultimo_log >= INTERVALO_LOG:
            # Estos sensores se leen SOLO al registrar, para no frenar el control:
            bateria = bot.battery()
            luz = bot.brightness()
            sonido = bot.loudness()
            escritor.writerow([
                round(ahora - inicio, 2),   # segundos desde el inicio
                round(distancia, 1),
                bateria,
                luz,
                sonido,
                accion,
            ])
            archivo_csv.flush()             # asegura que se escribe ya en disco
            ultimo_log = ahora

        # Lectura en vivo en la terminal
        print(f"Distancia: {distancia:5.1f} cm   Accion: {accion:10s}", end="\r")

        time.sleep(0.05)

finally:
    # Pase lo que pase (ESC, error, Ctrl+C): parar el robot, cerrar el archivo y desconectar.
    bot.stop()
    bot.disconnect()
    archivo_csv.close()
    print("\nDesconectado. Datos guardados en:", nombre_csv)
