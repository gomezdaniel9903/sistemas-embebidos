"""
Conducir el mBot2 desde el teclado del PC, por Bluetooth (Opción B).

Corre en tu ORDENADOR (no se sube al robot). Usa la libreria de la comunidad
'mbot_python' (DrorSh) para hablar con el mBot2 por el mismo canal "Live Mode"
que usa mBlock, y 'pynput' para leer las teclas.

Requisitos (una sola vez):
    pip install -e .        # dentro de la carpeta del repo mbot_python
    pip install pynput

Uso:
    - Enciende el mBot2 (que NO este conectado a mBlock ni al movil).
    - Ejecuta:  py conducir_mbot2_teclado.py
    - Flechas para conducir. ESC para salir.
"""

import time
from mbot2 import MBot2
from pynput import keyboard

# ---- Ajustes ----
VELOCIDAD = 200     # 0-100
UMBRAL = 10        # cm: por debajo, se bloquea SOLO el avance

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

ultima_accion = None        # para no reenviar el mismo comando una y otra vez

try:
    while listener.running:
        distancia = bot.distance()      # lectura del ultrasonico, en cm

        # Decidir la accion segun las teclas + freno de seguridad.
        # Fijate que el "distancia > UMBRAL" solo afecta al AVANCE:
        # asi puedes retroceder y girar aunque tengas un obstaculo delante.
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
                bot.turn_left(VELOCIDAD*0.25)
            elif accion == "derecha":
                bot.turn_right(VELOCIDAD*0.25)
            else:
                bot.stop()
            ultima_accion = accion

        # Mostrar la distancia en vivo en la terminal
        print(f"Distancia: {distancia:5.1f} cm   Accion: {accion:10s}", end="\r")

        time.sleep(0.05)

finally:
    # Pase lo que pase (ESC, error, Ctrl+C), dejar el robot parado y desconectar.
    bot.stop()
    bot.disconnect()
    print("\nDesconectado. Hasta luego!")
