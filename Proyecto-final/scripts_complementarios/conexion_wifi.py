"""
pc_control_wifi.py  -  Corre en el PC.

Manda comandos al robot por Wi-Fi (UDP). El robot debe tener cargado
'robot_wifi_abordo.py' y estar encendido en la MISMA red Wi-Fi que el PC.

No usa Bluetooth ni la libreria mbot2: solo envia texto por UDP.

Requisitos:
    pip install customtkinter

Uso:
    python pc_control_wifi.py
    -> escribe la IP que muestra el robot en su pantalla, elige Manual o Pista.
       En manual, la ventana debe tener el foco para que las flechas funcionen.
"""

import socket
import customtkinter as ctk

IP_ROBOT_DEFECTO = "10.243.112.31"   # la que muestre el robot en su pantalla
PUERTO = 8888

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control mBot2 (Wi-Fi)")
        self.geometry("400x430")
        self.modo = "parar"
        self.direccion = "parar"

        ctk.CTkLabel(self, text="Control mBot2 por Wi-Fi",
                     font=("", 20, "bold")).pack(pady=(16, 8))

        # IP del robot
        fila = ctk.CTkFrame(self); fila.pack(pady=6)
        ctk.CTkLabel(fila, text="IP del robot:").grid(row=0, column=0, padx=6)
        self.ip_entry = ctk.CTkEntry(fila, width=170)
        self.ip_entry.insert(0, IP_ROBOT_DEFECTO)
        self.ip_entry.grid(row=0, column=1, padx=6)

        # Selector de modo
        modo_f = ctk.CTkFrame(self); modo_f.pack(pady=12)
        ctk.CTkButton(modo_f, text="Manual", command=self.modo_manual).grid(row=0, column=0, padx=6)
        ctk.CTkButton(modo_f, text="Pista", command=self.modo_pista).grid(row=0, column=1, padx=6)
        ctk.CTkButton(modo_f, text="Parar", fg_color="gray30",
                      command=self.modo_parar).grid(row=0, column=2, padx=6)

        self.lbl = ctk.CTkLabel(self, text="Modo: parar", font=("", 16))
        self.lbl.pack(pady=12)
        ctk.CTkLabel(self, text="Manual: conduce con las flechas\n(la ventana debe tener el foco)",
                     text_color="gray").pack(pady=(0, 6))

        # Teclas para el modo manual
        
        for k, d in [("Up", "adelante"), ("Down", "atras"),
                     ("Left", "izquierda"), ("Right", "derecha")]:
            self.bind("<KeyPress-" + k + ">", lambda e, d=d: self.set_dir(d))
            self.bind("<KeyRelease-" + k + ">", lambda e: self.set_dir("parar"))

        self.loop_envio()

    def ip(self):
        return self.ip_entry.get().strip()

    def enviar(self, cmd, veces=1):
        for _ in range(veces):
            try:
                sock.sendto(cmd.encode(), (self.ip(), PUERTO))
            except Exception:
                pass

    # ---- Botones de modo ----
    def modo_manual(self):
        self.modo = "manual"
        self.direccion = "parar"
        self.lbl.configure(text="Modo: manual")

    def modo_pista(self):
        # 'Dispara y olvida': el robot sigue la linea el solo (y puede parar
        # con el marcador rojo). Por eso no lo reenviamos en el bucle.
        self.modo = "pista"
        self.enviar("PISTA", 3)          # 3 veces por si se pierde un paquete
        self.lbl.configure(text="Modo: pista")

    def modo_parar(self):
        self.modo = "parar"
        self.enviar("PARAR", 3)
        self.lbl.configure(text="Modo: parar")

    def set_dir(self, d):
        if self.modo == "manual":
            self.direccion = d

    # ---- Reenvio periodico (solo en manual, por seguridad) ----
    def loop_envio(self):
        if self.modo == "manual":
            # 10 veces/seg: si se pierde un paquete, enseguida llega otro,
            # y el watchdog del robot para si el PC deja de enviar.
            self.enviar("MANUAL " + self.direccion)
        self.after(100, self.loop_envio)

if __name__ == "__main__":
    App().mainloop()