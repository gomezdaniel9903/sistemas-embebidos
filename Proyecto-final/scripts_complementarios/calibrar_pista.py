from mbot2 import MBot2
import time

bot = MBot2()

def direccion_linea(colores):
    negros = [c == "black" for c in colores]
    if all(negros):
        return "recto"
    if negros[0]:   return "izquierda"
    if negros[3]:   return "derecha"
    if negros[1] or negros[2]: return "recto"
    return "perdida"

try:
    while True:
        colores = [bot.eval(f"mbuild.quad_rgb_sensor.get_color_sta({i})") for i in (4, 3, 2, 1)]
        print("Izq -> Der:", colores, " -> decision:", direccion_linea(colores))
        time.sleep(0.3)
except KeyboardInterrupt:
    bot.stop(); bot.disconnect()