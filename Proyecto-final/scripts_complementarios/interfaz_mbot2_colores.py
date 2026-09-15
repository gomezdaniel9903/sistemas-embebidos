"""
Interfaz grafica para el mBot2 (Opcion B: Python en el PC por Bluetooth).

Permite elegir con botones entre:
  - MODO MANUAL: conduces con las flechas (+ freno por ultrasonico, velocidad
    ajustable con + / -, y LED que cambia de color segun la velocidad).
  - MODO PISTA:  seguimiento de linea con el sensor Quad RGB, a VELOCIDAD BAJA
    y CONSTANTE (asi la latencia del Bluetooth no arruina el seguimiento).

Ademas: telemetria en vivo, registro en CSV y melodia de despedida al desconectar.

ARQUITECTURA (importante):
  - La ventana (customtkinter) corre en el hilo principal con su propio bucle.
  - TODO el dialogo con el robot ocurre en UN hilo de trabajo aparte, para no
    congelar la ventana y para no chocar con el asyncio interno de la libreria.
  - Los botones solo cambian variables de 'estado'; el hilo de trabajo las lee.
  - La ventana se refresca leyendo 'telemetria' con app.after(...).

Requisitos (una sola vez):
    pip install -e .            # dentro de la carpeta del repo mbot_python
    pip install customtkinter

Nota: el sensor Quad RGB debe estar CALIBRADO una vez (se hace desde mBlock,
colocandolo sobre blanco). Sin calibrar, el seguimiento va erratico.

Uso:
    python interfaz_mbot2.py
    -> pulsa "Conectar", luego elige Manual o Pista. La ventana debe tener el
       foco para que las flechas funcionen en modo manual.
"""

import time
import csv
import threading
from datetime import datetime

import customtkinter as ctk
from mbot2 import MBot2

# ==================== AJUSTES ====================
VEL_INICIAL = 50        # velocidad manual inicial (0-100)
PASO = 10               # cuanto sube/baja con + / -
VEL_MIN, VEL_MAX = 10, 100
UMBRAL = 10             # cm: por debajo, se bloquea el avance (modo manual)

BASE_PISTA = 10         # velocidad de crucero en modo pista
GIRO = 4              # cuanto corrige al girar (suave < BASE_PISTA; pivota si es mayor)

INTERVALO_LOG = 0.5     # segundos entre filas del CSV
INTERVALO_BAT = 2.0     # segundos entre lecturas de bateria (es lenta)

# Sensor Quad RGB via la puerta trasera eval. get_color_sta(pastilla) devuelve
# el color como texto ("black" en la linea, "white" en el fondo, y "red"/"green"/
# "blue"... en los marcadores). Con una sola lectura de las 4 pastillas dirigimos
# Y detectamos marcadores. (En este firmware el offset no funciona; esto si.)
GET_COLOR = "mbuild.quad_rgb_sensor.get_color_sta({})"   # {} = pastilla 1..4

# --- Notas naturales para la melodia de despedida (Hz) ---
NOTAS = {"SOL4": 392, "LA4": 440, "SI4": 494, "DO5": 523,
         "RE5": 587, "MI5": 659, "FA5": 698, "SOL5": 784}
CUMPLEANOS = [
    ("SOL4", .5), ("SOL4", .5), ("LA4", 1), ("SOL4", 1), ("DO5", 1), ("SI4", 1.5),
    ("SOL4", .5), ("SOL4", .5), ("LA4", 1), ("SOL4", 1), ("RE5", 1), ("DO5", 1.5),
    ("SOL4", .5), ("SOL4", .5), ("SOL5", 1), ("MI5", 1), ("DO5", 1), ("SI4", 1), ("LA4", 1.5),
    ("FA5", .5), ("FA5", .5), ("MI5", 1), ("DO5", 1), ("RE5", 1), ("DO5", 1.5),
]
TIEMPO = 0.4            # segundos por tiempo musical

# ==================== ESTADO COMPARTIDO ====================
# Lo escriben los botones/teclas; lo lee el hilo de trabajo.
estado = {
    "ejecutando": False,   # el hilo de control esta activo
    "conectado": False,
    "modo": "detenido",    # "manual" | "pista" | "detenido"
    "velocidad": VEL_INICIAL,
}
# Teclas de direccion (booleanos: no hay que iterar, asi es seguro entre hilos)
teclas = {"up": False, "down": False, "left": False, "right": False}

# Telemetria que muestra la ventana (protegida por un lock)
telemetria = {"estado": "Sin conectar", "distancia": "--", "offset": "--",
              "bateria": "--", "velocidad": VEL_INICIAL, "modo": "detenido"}
lock = threading.Lock()

def set_tel(**kwargs):
    with lock:
        telemetria.update(kwargs)

# ==================== FUNCIONES AUXILIARES ====================
def color_por_velocidad(v):
    if v <= 33:
        return (0, 255, 0)      # verde  -> lento
    elif v <= 66:
        return (255, 150, 0)    # ambar  -> medio
    else:
        return (255, 0, 0)      # rojo   -> rapido

def leer_colores(bot):
    """Color de las 4 pastillas, de izquierda a derecha. None si falla."""
    try:
        return [bot.eval(GET_COLOR.format(i)) for i in (4, 3, 2, 1)]
    except Exception:
        return None

def direccion_linea(colores):
    """Decide el giro para una linea DELGADA. Orden izq->der: [L2, L1, R1, R2].
    - Un sensor de un LADO ve negro -> el robot se desvio: gira hacia ese lado.
    - Solo los CENTRALES ven negro -> recto (zona muerta: evita serpenteo).
    - Ninguno ve negro -> linea perdida."""
    negros = [c == "black" for c in colores]
    print(negros)
    if (negros[1] and negros[2] ) and (not negros[0] and not negros[3]):
        return "recto"                 # cruce (todo negro): sigue recto
    lado_izq = negros[0]               # L2 (extremo izquierdo)
    centro   = negros[1] or negros[2]  # L1 o R1 (centrales)
    lado_der = negros[3]               # R2 (extremo derecho)
    if lado_izq:
        return "izquierda"
    elif lado_der:
        return "derecha"
    elif centro:
        return "recto"
    else:
        return "perdida"

def color_marcador(colores):
    """Devuelve 'red'/'green'/'blue'/'yellow' si alguna pastilla lo ve; si no, ''."""
    for c in colores:
        if c in ("red", "green", "blue","yellow"):
            return c
    return ""

def tocar_cumpleanos(bot):
    try:
        bot.volume(80)
        for nota, t in CUMPLEANOS:
            dur = t * TIEMPO
            bot.beep(NOTAS[nota], dur * 0.85)
            time.sleep(dur)
    except Exception:
        pass

# ==================== HILO DE CONTROL (todo el I/O del robot) ====================
def bucle_control():
    bot = None
    archivo_csv = None
    ultimo_giro = ''
    try:
        set_tel(estado="Conectando...")
        bot = MBot2()                      # conexion Bluetooth (bloqueante)
        estado["conectado"] = True
        set_tel(estado="Conectado")

        nombre_csv = "datos_mbot2_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
        archivo_csv = open(nombre_csv, "w", newline="", encoding="utf-8")
        escritor = csv.writer(archivo_csv)
        escritor.writerow(["tiempo_s", "modo", "distancia_cm", "offset",
                           "velocidad", "bateria"])

        modo_anterior = None
        ultima_accion = ultima_vel = ultimo_color = None
        color_actuado = None    # anti-rebote: ultimo marcador ya atendido
        bateria = "--"
        inicio = time.time()
        ultimo_log = ultima_bat = inicio

        while estado["ejecutando"]:
            modo = estado["modo"]
            vel = estado["velocidad"]
            distancia = "--"
            offset = "--"

            # Al cambiar de modo: parar y resetear
            if modo != modo_anterior:
                try:
                    bot.stop()
                except Exception:
                    pass
                ultima_accion = ultima_vel = None
                color_actuado = None
                modo_anterior = modo

            # ---------- MODO MANUAL ----------
            if modo == "manual":
                distancia = bot.distance()
                if teclas["up"] and distancia > UMBRAL:
                    accion = "adelante"
                elif teclas["down"]:
                    accion = "atras"
                elif teclas["left"]:
                    accion = "izquierda"
                elif teclas["right"]:
                    accion = "derecha"
                else:
                    accion = "parar"

                if accion != ultima_accion or (accion != "parar" and vel != ultima_vel):
                    if accion == "adelante":   bot.forward(vel)
                    elif accion == "atras":    bot.backward(vel)
                    elif accion == "izquierda": bot.turn_left(vel)
                    elif accion == "derecha":  bot.turn_right(vel)
                    else:                      bot.stop()
                    ultima_accion, ultima_vel = accion, vel

                color = color_por_velocidad(vel)
                if color != ultimo_color:
                    bot.led(*color)
                    ultimo_color = color

            # ---------- MODO PISTA (linea + marcadores de color) ----------
            elif modo == "pista":
                colores = leer_colores(bot)
                if colores is None:
                    bot.stop()
                    offset = "error"
                else:
                    marcador = color_marcador(colores)
                    if not marcador:
                        color_actuado = None        # rearmado cuando ya no hay color

                    if marcador and marcador != color_actuado:
                        # Actuar UNA sola vez por marcador
                        color_actuado = marcador
                        offset = marcador
                        if marcador == "red":
                            bot.drive(0, -0) 
                            time.sleep(5)
                            bot.drive(BASE_PISTA, -BASE_PISTA) 
                            time.sleep(0.6)
                            # bot.stop()
                            # estado["modo"] = "detenido"          # ROJO -> parar
                        elif marcador == "green":
                            bot.drive(BASE_PISTA, -BASE_PISTA)     # VERDE -> recto
                            time.sleep(0.6)
                        elif marcador == "blue":
                            bot.run('cyberpi.audio.play("Bye")')
                            bot.drive(BASE_PISTA, -BASE_PISTA) 
                            time.sleep(0.6)
                        elif marcador == "yellow":
                            bot.run('cyberpi.audio.play("Hello")')
                            bot.drive(BASE_PISTA, -BASE_PISTA) 
                            time.sleep(0.6)
                    elif marcador:
                        # marcador ya atendido: avanza recto mientras lo cruza
                        bot.drive(BASE_PISTA, -BASE_PISTA)
                        offset = marcador
                    else:
                        # Seguir la linea negra (esquema discreto para linea delgada)
                        d = direccion_linea(colores)
                        
                        print(d)
                        if d == "recto":
                            bot.drive(BASE_PISTA, -BASE_PISTA)
                        elif d == "izquierda":
                            bot.drive( - GIRO, -BASE_PISTA - GIRO  )
                        elif d == "derecha":
                            bot.drive(BASE_PISTA + GIRO, BASE_PISTA - GIRO)
                        else:
                            if ultima_accion == "izquierda":
                                bot.drive( GIRO, - GIRO)
                            if ultima_accion == "derecha":
                                bot.drive( - GIRO,  - GIRO  )    
                            if ultima_accion in ["recto", "perdida", '']:
                                bot.drive( - GIRO,  - GIRO  )
                            bot.stop()          # linea perdida
                        offset = d
                        ultima_accion = d

            # ---------- DETENIDO ----------
            else:
                if ultima_accion != "parar":
                    bot.stop()
                    ultima_accion = "parar"

            # ---------- Bateria (lenta: cada pocos segundos) ----------
            ahora = time.time()
            if ahora - ultima_bat >= INTERVALO_BAT:
                try:
                    bateria = bot.battery()
                except Exception:
                    pass
                ultima_bat = ahora

            # ---------- Telemetria a la ventana ----------
            set_tel(estado="Conectado", distancia=distancia, offset=offset,
                    bateria=bateria, velocidad=vel, modo=modo)

            # ---------- Registro CSV ----------
            if ahora - ultimo_log >= INTERVALO_LOG:
                escritor.writerow([round(ahora - inicio, 2), modo, distancia,
                                   offset, vel, bateria])
                archivo_csv.flush()
                ultimo_log = ahora

            time.sleep(0.02)

    except Exception as e:
        set_tel(estado="Error: " + str(e))
    finally:
        # Salida limpia pase lo que pase
        if bot is not None:
            try:
                bot.stop(); bot.led_off()
                # tocar_cumpleanos(bot)        # melodia de despedida
                bot.disconnect()
            except Exception:
                pass
        if archivo_csv is not None:
            archivo_csv.close()
        estado["conectado"] = False
        set_tel(estado="Desconectado")

# ==================== VENTANA (customtkinter) ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control mBot2")
        self.geometry("420x460")

        ctk.CTkLabel(self, text="Control mBot2",
                     font=("", 22, "bold")).pack(pady=(16, 4))

        # --- Panel de conexion ---
        fila = ctk.CTkFrame(self); fila.pack(pady=6)
        self.btn_con = ctk.CTkButton(fila, text="Conectar", command=self.conectar)
        self.btn_con.grid(row=0, column=0, padx=6)
        self.btn_des = ctk.CTkButton(fila, text="Desconectar", command=self.desconectar,
                                     state="disabled")
        self.btn_des.grid(row=0, column=1, padx=6)

        # --- Selector de modo ---
        modo_f = ctk.CTkFrame(self); modo_f.pack(pady=10)
        ctk.CTkLabel(modo_f, text="Modo:").grid(row=0, column=0, padx=6)
        self.btn_manual = ctk.CTkButton(modo_f, text="Manual",
                                        command=lambda: self.set_modo("manual"))
        self.btn_manual.grid(row=0, column=1, padx=6)
        self.btn_pista = ctk.CTkButton(modo_f, text="Pista",
                                       command=lambda: self.set_modo("pista"))
        self.btn_pista.grid(row=0, column=2, padx=6)
        self.btn_parar = ctk.CTkButton(modo_f, text="Parar", fg_color="gray30",
                                       command=lambda: self.set_modo("detenido"))
        self.btn_parar.grid(row=0, column=3, padx=6)

        # --- Velocidad (manual) ---
        vel_f = ctk.CTkFrame(self); vel_f.pack(pady=6)
        ctk.CTkButton(vel_f, text="Vel -", width=70,
                      command=lambda: self.cambiar_vel(-PASO)).grid(row=0, column=0, padx=6)
        ctk.CTkButton(vel_f, text="Vel +", width=70,
                      command=lambda: self.cambiar_vel(+PASO)).grid(row=0, column=1, padx=6)

        # --- Telemetria ---
        tel_f = ctk.CTkFrame(self); tel_f.pack(pady=12, fill="x", padx=20)
        self.lbl_estado = ctk.CTkLabel(tel_f, text="Estado: Sin conectar")
        self.lbl_estado.pack(anchor="w", padx=10, pady=2)
        self.lbl_modo = ctk.CTkLabel(tel_f, text="Modo: --")
        self.lbl_modo.pack(anchor="w", padx=10, pady=2)
        self.lbl_dist = ctk.CTkLabel(tel_f, text="Distancia: -- cm")
        self.lbl_dist.pack(anchor="w", padx=10, pady=2)
        self.lbl_off = ctk.CTkLabel(tel_f, text="Offset linea: --")
        self.lbl_off.pack(anchor="w", padx=10, pady=2)
        self.lbl_vel = ctk.CTkLabel(tel_f, text="Velocidad: --")
        self.lbl_vel.pack(anchor="w", padx=10, pady=2)
        self.lbl_bat = ctk.CTkLabel(tel_f, text="Bateria: --")
        self.lbl_bat.pack(anchor="w", padx=10, pady=2)

        ctk.CTkLabel(self, text="Manual: flechas para conducir | + / - velocidad",
                     text_color="gray").pack(pady=(4, 0))

        # Teclas (la ventana debe tener el foco)
        for k, d in [("Up", "up"), ("Down", "down"), ("Left", "left"), ("Right", "right")]:
            self.bind(f"<KeyPress-{k}>", lambda e, d=d: self.tecla(d, True))
            self.bind(f"<KeyRelease-{k}>", lambda e, d=d: self.tecla(d, False))
        for k in ("plus", "KP_Add", "equal"):
            self.bind(f"<KeyPress-{k}>", lambda e: self.cambiar_vel(+PASO))
        for k in ("minus", "KP_Subtract"):
            self.bind(f"<KeyPress-{k}>", lambda e: self.cambiar_vel(-PASO))

        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.actualizar_ui()

    # ---- Acciones de la interfaz (solo cambian 'estado') ----
    def conectar(self):
        if estado["ejecutando"]:
            return
        estado["ejecutando"] = True
        estado["modo"] = "detenido"
        threading.Thread(target=bucle_control, daemon=True).start()
        self.btn_con.configure(state="disabled")
        self.btn_des.configure(state="normal")

    def desconectar(self):
        estado["ejecutando"] = False        # el hilo hace la salida limpia
        self.btn_con.configure(state="normal")
        self.btn_des.configure(state="disabled")

    def set_modo(self, m):
        estado["modo"] = m

    def cambiar_vel(self, delta):
        estado["velocidad"] = max(VEL_MIN, min(VEL_MAX, estado["velocidad"] + delta))

    def tecla(self, direccion, valor):
        teclas[direccion] = valor

    def cerrar(self):
        estado["ejecutando"] = False
        self.after(300, self.destroy)       # da un instante a la salida limpia

    # ---- Refresco periodico de la telemetria ----
    def actualizar_ui(self):
        with lock:
            t = dict(telemetria)
        self.lbl_estado.configure(text=f"Estado: {t['estado']}")
        self.lbl_modo.configure(text=f"Modo: {t['modo']}")
        self.lbl_dist.configure(text=f"Distancia: {t['distancia']} cm")
        self.lbl_off.configure(text=f"Offset linea: {t['offset']}")
        self.lbl_vel.configure(text=f"Velocidad: {t['velocidad']}")
        self.lbl_bat.configure(text=f"Bateria: {t['bateria']}")
        self.after(100, self.actualizar_ui)

if __name__ == "__main__":
    App().mainloop()