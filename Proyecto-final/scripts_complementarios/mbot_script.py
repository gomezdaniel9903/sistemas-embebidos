# =====================================================================
#  robot_wifi_abordo.py
#  SUBIR AL ROBOT con mBlock (Editor de Python, modo SUBIR).
# =====================================================================
import cyberpi
import mbot2
import mbuild
import time

try:
    import socket
except ImportError:
    import usocket as socket

# ===================== AJUSTES =====================
SSID = "CRISF"          # <-- tu red Wi-Fi
PASSWORD = "Cris1234"      # <-- tu contraseña
PUERTO = 8888

VEL_MANUAL = 20      # potencia en manual
GIRO_MANUAL = 40     # potencia de giro en manual
BASE_PISTA = 15      # velocidad de crucero en pista
WATCHDOG = 0.4       # tiempo de seguridad
KP = 0.4             # constante proporcional de seguimiento

# ============ MOTORES (Signo del motor derecho invertido) ============
def mover(izq, der):
    mbot2.drive_power(izq, -der)  # <-- Inversión de polaridad aplicada aquí

def parar():
    mbot2.drive_power(0, 0)

# ===================== CONEXION WIFI =====================
cyberpi.display.show_label("Conectando WiFi...", 12, 0, 0)
cyberpi.wifi.connect(SSID, PASSWORD)
while not cyberpi.wifi.is_connect():
    time.sleep(0.3)
    
cyberpi.display.show_label("Enviando lista...", 12, 0, 0)
texto = " ".join(dir(cyberpi.wifi))

cyberpi.display.clear()
cyberpi.display.show_label("WiFi OK", 16, 0, 0)
cyberpi.display.show_label("Puerto: " + str(PUERTO), 12, 0, 45)

# ===================== SOCKET UDP =====================
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(("WIFI: " + texto).encode(), ("255.255.255.255", 9999))
time.sleep(1)
s.bind(("0.0.0.0", PUERTO))
s.settimeout(0.02)

# ===================== ESTADO =====================
modo = "parar"             # "parar" | "manual" | "pista"
direccion = "parar"        # dirección actual en manual
color_actuado = None       # anti-rebote de marcadores
ultimo_comando = time.time()

# ===================== SENSOR / RUTINAS =====================
def leer_colores():
    c = []
    for i in (4, 3, 2, 1):          # izquierda -> derecha
        c.append(mbuild.quad_rgb_sensor.get_color_sta(i))
    return c

def paso_pista():
    global color_actuado, modo
    
    # --- 1. Marcadores de color ---
    colores = leer_colores()
    marcador = ""
    for c in colores:
        if c in ("red", "green", "blue", "yellow"):
            marcador = c
            break
            
    if marcador == "":
        color_actuado = None
        
    if marcador != "" and marcador != color_actuado:
        color_actuado = marcador
        if marcador == "red":
            time.sleep(2.6)  
        elif marcador == "green":
            pass
        elif marcador == "blue":
            cyberpi.audio.play("Bye")
        elif marcador == "yellow":
            cyberpi.audio.play("Hello")
        return
        
    if marcador != "":
        mover(BASE_PISTA, BASE_PISTA)
        return
    
    # --- 2. Control Proporcional mBot2 ---
    offset = mbuild.quad_rgb_sensor.get_offset_track(1)
    
    izq = BASE_PISTA - (offset * KP)
    der = BASE_PISTA + (offset * KP)
    
    mover(izq, der)

def ejecutar_manual(d):
    if d == "adelante":
        mover(VEL_MANUAL, VEL_MANUAL)
    elif d == "atras":
        mover(-VEL_MANUAL, -VEL_MANUAL)
    elif d == "izquierda":
        mover(-GIRO_MANUAL, GIRO_MANUAL)
    elif d == "derecha":
        mover(GIRO_MANUAL, -GIRO_MANUAL)
    else:
        parar()

# ===================== BUCLE PRINCIPAL =====================
while True:
    try:
        datos, _ = s.recvfrom(64)
        msg = datos.decode().strip()
        ultimo_comando = time.time()
        if msg == "PISTA":
            modo = "pista"
        elif msg == "PARAR":
            modo = "parar"
        elif msg[:6] == "MANUAL":
            modo = "manual"
            partes = msg.split()
            direccion = partes[1] if len(partes) > 1 else "parar"
    except Exception:
        pass

    if modo == "manual" and time.time() - ultimo_comando > WATCHDOG:
        direccion = "parar"

    if modo == "pista":
        cyberpi.display.show_label("Pista", 12, 0, 0)
        paso_pista()
    elif modo == "manual":
        cyberpi.display.show_label("Manual", 12, 0, 0)
        ejecutar_manual(direccion)
    else:
        cyberpi.display.show_label("Parado", 12, 0, 0)
        parar()

    time.sleep(0.01)