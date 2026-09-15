from mbot2 import MBot2
import time

bot = MBot2()
bot.run("mbuild.quad_rgb_sensor.set_line_track_mode()")
try:
    while True:
        # pastilla 1 = extremo derecho ... pastilla 4 = extremo izquierdo
        estados = [bot.eval(f"mbuild.quad_rgb_sensor.is_line({i})") for i in (4, 3, 2, 1)]
        offset = bot.eval("cyberpi.quad_rgb_sensor_1.get_line_track_offset()")
        print("Izq -> Der:", estados, " | Offset:", offset)
        time.sleep(0.3)
except KeyboardInterrupt:
    bot.stop(); bot.disconnect()