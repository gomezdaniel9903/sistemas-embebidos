from mbot2 import MBot2
import time

bot = MBot2()
try:
    while True:
        # color de cada pastilla: 1 = extremo derecho ... 4 = extremo izquierdo
        colores = [bot.eval(f"mbuild.quad_rgb_sensor.get_color_sta({i})") for i in (4, 3, 2, 1)]
        print("Izq -> Der:", colores)
        time.sleep(0.3)
except KeyboardInterrupt:
    bot.stop(); bot.disconnect()