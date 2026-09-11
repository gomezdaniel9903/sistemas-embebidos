# -*- coding: utf-8 -*-
"""
Cinemática directa por Denavit-Hartenberg — convención MODIFICADA (Craig).
Manipulador de 5 GDL (Eje 1 prismático, Ejes 2-5 de revolución).
Genera la gráfica del robot, la imagen de varias poses y un GIF animado.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# ============================================================
#   1) TABLA DE PARÁMETROS DH — convención MODIFICADA (Craig)
# ============================================================
DH = [
    # alpha_{i-1},  a_{i-1},  theta_i,   d_i,    sigma
    [ np.pi/2,      0.00,     np.pi/2,   0.00,   1],   # Eje 1 - PRISMATICA (variable d1)
    [ 0.0,          0.33,     0.0,       0.00,   0],   # Eje 2 - revolucion (variable th2)
    [ 0.0,          0.40,     0.0,       0.00,   0],   # Eje 3 - revolucion (variable th3)
    [ np.pi/2,      0.00,     0.0,       0.16,   0],   # Eje 4 - revolucion (variable th4)
    [-np.pi/2,      0.00,     0.0,       0.00,   0],   # Eje 5 - revolucion (variable th5)
]

# Poses ("pasos") a mostrar. Primer valor d1 [m], luego th2..th5 [rad].
# (angulos de revolucion negados respecto a la version anterior para que el
#  brazo se extienda hacia ADELANTE, +X, en vez de hacia atras)
Q_POSE   = [0.10, np.deg2rad(-30), np.deg2rad(45), np.deg2rad(-60), np.deg2rad(0)]
Q_POSE_2 = [0.05, np.deg2rad(-80), np.deg2rad(35), np.deg2rad(-60), np.deg2rad(180)]
Q_POSE_3 = [-0.1, np.deg2rad(-50), np.deg2rad(25), np.deg2rad(-60), np.deg2rad(0)]
Q_POSE_4 = [-0.2, np.deg2rad(-40), np.deg2rad(15), np.deg2rad(-60), np.deg2rad(180)]


# ============================================================
#   2) MATRIZ DE TRANSFORMACION DH MODIFICADA (Craig)
# ============================================================
def dh_matrix(alpha, a, theta, d):
    ct, st = np.cos(theta), np.sin(theta)
    ca, sa = np.cos(alpha), np.sin(alpha)
    return np.array([
        [ct,      -st,      0.0,  a      ],
        [st * ca,  ct * ca, -sa, -sa * d ],
        [st * sa,  ct * sa,  ca,  ca * d ],
        [0.0,      0.0,      0.0, 1.0    ],
    ])


# ============================================================
#   3) CINEMATICA DIRECTA
# ============================================================
def cinematica_directa(q, dh=DH):
    T = np.eye(4)
    puntos = [T[:3, 3].copy()]
    frames = [T.copy()]
    for i, (alpha, a, theta, d, sigma) in enumerate(dh):
        if sigma == 0:
            theta = theta + q[i]
        else:
            d = d + q[i]
        T = T @ dh_matrix(alpha, a, theta, d)
        puntos.append(T[:3, 3].copy())
        frames.append(T.copy())
    return np.array(puntos), frames


# ============================================================
#   5) VISUALIZACION
# ============================================================
def _ejes_iguales(ax, pts):
    pts = np.asarray(pts)
    centro = pts.mean(axis=0)
    rango = (pts.max(axis=0) - pts.min(axis=0)).max() / 2 or 1.0
    ax.set_xlim(centro[0] - rango, centro[0] + rango)
    ax.set_ylim(centro[1] - rango, centro[1] + rango)
    ax.set_zlim(centro[2] - rango, centro[2] + rango)
    try:
        ax.set_box_aspect([1, 1, 1])
    except Exception:
        pass


def dibujar_ejes(ax, T, escala):
    o = T[:3, 3]
    x, y, z = T[:3, 0], T[:3, 1], T[:3, 2]
    ax.quiver(*o, *x, length=escala, color='r', linewidth=1.2)
    ax.quiver(*o, *y, length=escala, color='g', linewidth=1.2)
    ax.quiver(*o, *z, length=escala, color='b', linewidth=1.2)


def _dibujar_robot(ax, q, dh=DH, color='0.2', label=None, mostrar_ejes=False,
                   efector=True, color_ef=None, label_ef=None, aprox=False):
    puntos, frames = cinematica_directa(q, dh)
    ax.plot(puntos[:, 0], puntos[:, 1], puntos[:, 2],
            '-o', color=color, linewidth=2.5, markersize=6,
            markerfacecolor=color, label=label)
    if mostrar_ejes:
        tam = np.linalg.norm(puntos.max(axis=0) - puntos.min(axis=0))
        escala = 0.15 * (tam if tam > 0 else 1.0)
        for T in frames:
            dibujar_ejes(ax, T, escala)
    if efector:
        ef = puntos[-1]
        c = color_ef if color_ef is not None else color
        ax.scatter(*ef, color=c, marker='*', s=180, edgecolors='k',
                   linewidths=0.7, depthshade=False, zorder=6, label=label_ef)
        if aprox:
            tam = np.linalg.norm(puntos.max(axis=0) - puntos.min(axis=0))
            escala = 0.18 * (tam if tam > 0 else 1.0)
            z = frames[-1][:3, 2]
            ax.quiver(*ef, *z, length=escala, color=c, linewidth=2)
    return puntos


def plot_robot(q, dh=DH, mostrar_ejes=True, aprox=True):
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection='3d')
    puntos = _dibujar_robot(ax, q, dh, color='0.2', label='Eslabones',
                            mostrar_ejes=mostrar_ejes, efector=True,
                            color_ef='red', label_ef='Efector final', aprox=aprox)
    ax.scatter(*puntos[0], color='k', s=70, label='Base')
    ax.set_title('Manipulador 5 GDL - Cinematica directa (DH modificada)')
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _ejes_iguales(ax, puntos)
    ax.legend()
    plt.tight_layout()
    return fig


def plot_robots(poses, dh=DH, nombres=None, mostrar_ejes=False):
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection='3d')
    colores = plt.cm.tab10.colors
    todos = []
    for i, q in enumerate(poses):
        etiqueta = nombres[i] if nombres else ('Pose %d' % (i + 1))
        pts = _dibujar_robot(ax, q, dh, color=colores[i % len(colores)],
                             label=etiqueta, mostrar_ejes=mostrar_ejes, efector=True)
        todos.append(pts)
    ax.scatter(0, 0, 0, color='k', s=70, label='Base')
    ax.plot([], [], [], linestyle='None', marker='*', markersize=13,
            markerfacecolor='0.3', markeredgecolor='k', label='Efector final')
    todos = np.vstack(todos)
    ax.set_title('Manipulador 5 GDL - %d poses' % len(poses))
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _ejes_iguales(ax, todos)
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
#   5b) GUARDAR IMAGEN Y GIF
# ============================================================
def guardar_imagen(poses, ruta='robot_pasos.png', dh=DH, dpi=150, nombres=None):
    """Guarda en un PNG las poses superpuestas (los 'pasos' del robot)."""
    fig = plot_robots(poses, dh=dh, nombres=nombres)
    fig.savefig(ruta, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print("Imagen guardada:", ruta)
    return ruta


def _trayectoria(poses, pasos=14, pausa=5, cerrar=True):
    """Interpola entre poses consecutivas (con una pausa en cada una)."""
    seq = [np.array(p, float) for p in poses]
    if cerrar:
        seq = seq + [seq[0]]          # vuelve a la primera para un GIF en bucle
    qs = []
    for a, b in zip(seq[:-1], seq[1:]):
        qs += [a] * pausa                                   # pausa en la pose
        for t in np.linspace(0, 1, pasos, endpoint=False):
            qs.append(a + (b - a) * t)                       # transicion suave
    qs += [seq[-1]] * pausa
    return qs


def crear_gif(poses, ruta='robot.gif', dh=DH, pasos=14, pausa=5,
              fps=20, dpi=90, girar=False):
    """
    Genera un GIF del robot moviendose por las poses (pasos).
      pasos  : cuadros de transicion entre poses consecutivas
      pausa  : cuadros quieto en cada pose
      girar  : si True, la camara gira lentamente
    """
    qs = _trayectoria(poses, pasos, pausa)

    # limites fijos calculados con TODA la trayectoria (evita que salte la vista)
    allp = np.vstack([cinematica_directa(q, dh)[0] for q in qs])
    c = allp.mean(axis=0)
    r = (allp.max(axis=0) - allp.min(axis=0)).max() / 2 or 1.0

    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection='3d')

    def update(k):
        ax.cla()
        _dibujar_robot(ax, qs[k], dh, color='tab:blue',
                       mostrar_ejes=False, efector=True, color_ef='red')
        ax.scatter(0, 0, 0, color='k', s=60)
        ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
        try: ax.set_box_aspect([1, 1, 1])
        except Exception: pass
        azim = -60 + (360 * k / len(qs) if girar else 0)
        ax.view_init(elev=20, azim=azim)
        ax.set_title('Manipulador 5 GDL - movimiento por poses')
        ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')

    anim = animation.FuncAnimation(fig, update, frames=len(qs), interval=1000/fps)
    anim.save(ruta, writer=animation.PillowWriter(fps=fps), dpi=dpi)
    plt.close(fig)
    print("GIF guardado:", ruta, "(%d cuadros)" % len(qs))
    return ruta


# ============================================================
#   6) PROGRAMA PRINCIPAL
# ============================================================
if __name__ == '__main__':
    poses = [Q_POSE, Q_POSE_2, Q_POSE_3, Q_POSE_4]

    for i, q in enumerate(poses):
        pts, _ = cinematica_directa(q)
        print("Pose %d - efector final (x,y,z) [m]: %s" % (i + 1, np.round(pts[-1], 4)))

    # 1) Imagen con los 4 pasos superpuestos
    guardar_imagen(poses, 'Ejemplo-DH/robot_pasos.png')

    # 2) GIF del robot moviendose por los 4 pasos
    crear_gif(poses, 'Ejemplo-DH/robot.gif', girar=False)

    # (opcional) ver una figura en pantalla:
    # plot_robots(poses); plt.show()