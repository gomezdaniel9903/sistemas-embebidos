# -*- coding: utf-8 -*-
"""
Manipulador ARTICULADO de 4 GDL (todo revolucion):
  J1 giro de base | J2 hombro | J3 codo | J4 muñeca (cabeceo)
Convencion DH MODIFICADA (Craig).
Incluye: cinematica directa, dibujo con ejes, poses multiples, nube de puntos,
         guardar imagen de las poses y GIF animado.
Colores de los ejes (como tus laminas): Z = rojo, X = verde, Y = azul.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# ============================================================
#   1) CONFIGURACION   <-- EDITA AQUI
# ============================================================
H  = 0.20   # base -> hombro
A2 = 0.30   # brazo     (hombro -> codo)
A3 = 0.25   # antebrazo (codo -> muñeca)
AT = 0.10   # muñeca -> punta del gripper (herramienta)

def _tabla(q):
    t1, t2, t3, t4 = q
    return [
        (0.0,      0.0, t1, H ),   # {0}->{1}  J1 giro de base
        (np.pi/2,  0.0, t2, 0.),   # {1}->{2}  J2 hombro
        (0.0,      A2,  t3, 0.),   # {2}->{3}  J3 codo
        (0.0,      A3,  t4, 0.),   # {3}->{4}  J4 muñeca (cabeceo)
        (0.0,      AT,  0., 0.),   # {4}->tool herramienta (fija)
    ]

LIMITES = [
    (np.deg2rad(-180), np.deg2rad(180)),   # J1
    (np.deg2rad(-90),  np.deg2rad(90)),    # J2
    (np.deg2rad(-150), np.deg2rad(150)),   # J3
    (np.deg2rad(-120), np.deg2rad(120)),   # J4
]

# Poses ("pasos") a mostrar [theta1, theta2, theta3, theta4] (en grados)
Q_POSE   = np.deg2rad([  0, 120, -110, -40])   # parecida a la foto
Q_POSE_2 = np.deg2rad([ 45,  90,  -60, -20])
Q_POSE_3 = np.deg2rad([-40,  60,  -95,  30])
Q_POSE_4 = np.deg2rad([-15, 100,  -80, -25])


# ============================================================
#   2) MATRIZ DH MODIFICADA (Craig)
# ============================================================
def dh_matrix(alpha, a, theta, d):
    ct, st = np.cos(theta), np.sin(theta)
    ca, sa = np.cos(alpha), np.sin(alpha)
    return np.array([[ct,    -st,     0.0,  a     ],
                     [st*ca,  ct*ca, -sa,  -sa*d  ],
                     [st*sa,  ct*sa,  ca,   ca*d  ],
                     [0.0,    0.0,    0.0,  1.0   ]])


# ============================================================
#   3) CINEMATICA DIRECTA
# ============================================================
def cinematica_directa(q):
    T = np.eye(4)
    puntos = [T[:3, 3].copy()]
    frames = [T.copy()]
    for (al, a, th, d) in _tabla(q):
        T = T @ dh_matrix(al, a, th, d)
        puntos.append(T[:3, 3].copy())
        frames.append(T.copy())
    return np.array(puntos), frames


# ============================================================
#   4) NUBE DE PUNTOS (ESPACIO DE TRABAJO)
# ============================================================
def nube_de_puntos(limites=LIMITES, n_muestras=8000, semilla=0):
    rng = np.random.default_rng(semilla)
    bajos = np.array([l[0] for l in limites])
    altos = np.array([l[1] for l in limites])
    Q = rng.uniform(bajos, altos, size=(n_muestras, 4))
    nube = np.empty((n_muestras, 3))
    for k in range(n_muestras):
        pts, _ = cinematica_directa(Q[k])
        nube[k] = pts[-1]
    return nube


# ============================================================
#   5) VISUALIZACION
# ============================================================
def _iguales(ax, pts):
    pts = np.asarray(pts); c = pts.mean(0)
    r = (pts.max(0) - pts.min(0)).max() / 2 or 1.0
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    try: ax.set_box_aspect([1, 1, 1])
    except Exception: pass


def dibujar_ejes(ax, T, s):
    o = T[:3, 3]
    ax.quiver(*o, *T[:3, 2], length=s, color='r', linewidth=2.2)   # Z
    ax.quiver(*o, *T[:3, 0], length=s, color='g', linewidth=2.2)   # X
    ax.quiver(*o, *T[:3, 1], length=s, color='b', linewidth=1.3)   # Y


def _dibujar_robot(ax, q, color='0.25', color_art='orange', color_ef='red',
                   label=None, ejes=False, etiquetas=False, efector=True, aprox=False):
    pts, frames = cinematica_directa(q)
    ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], '-', color=color,
            linewidth=4, zorder=1, label=label)
    ax.scatter(pts[1:5, 0], pts[1:5, 1], pts[1:5, 2], color=color_art,
               edgecolors='k', s=45, zorder=3)
    diag = np.linalg.norm(pts.max(0) - pts.min(0)) or 1.0
    if ejes:
        s = 0.12 * diag
        for i in range(5):
            dibujar_ejes(ax, frames[i], s)
            if etiquetas:
                off = {1: (0, 0, 0.045), 2: (0.05, 0, -0.02)}.get(i, (0.03, 0, 0))
                o = frames[i][:3, 3]
                ax.text(o[0]+off[0], o[1]+off[1], o[2]+off[2], "{%d}" % i,
                        color='navy', fontsize=11, fontweight='bold')
    if efector:
        ef = pts[-1]
        ax.scatter(*ef, color=color_ef, marker='*', s=190, edgecolors='k',
                   depthshade=False, zorder=6)
        if aprox:
            ax.quiver(*ef, *frames[-1][:3, 2], length=0.18*diag,
                      color=color_ef, linewidth=2)
    return pts


def plot_ejes(q=Q_POSE):
    fig = plt.figure(figsize=(8, 7)); ax = fig.add_subplot(111, projection='3d')
    pts = _dibujar_robot(ax, q, ejes=True, etiquetas=True, aprox=False)
    ax.scatter(*pts[0], color='k', s=80)
    ax.set_title('Asignacion de ejes (DH modificada)\nZ=rojo  X=verde  Y=azul', fontsize=11)
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _iguales(ax, pts); ax.view_init(elev=12, azim=-72)
    plt.tight_layout(); return fig


def plot_robot(q, ejes=False, aprox=True):
    fig = plt.figure(figsize=(8, 7)); ax = fig.add_subplot(111, projection='3d')
    pts = _dibujar_robot(ax, q, ejes=ejes, etiquetas=ejes, aprox=aprox)
    ax.scatter(*pts[0], color='k', s=80)
    ax.set_title('Manipulador 4 GDL - cinematica directa')
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _iguales(ax, pts); ax.view_init(elev=15, azim=-70)
    plt.tight_layout(); return fig


def plot_robots(poses, nombres=None):
    fig = plt.figure(figsize=(8, 7)); ax = fig.add_subplot(111, projection='3d')
    cols = plt.cm.tab10.colors; todos = []
    for i, q in enumerate(poses):
        et = nombres[i] if nombres else ('Pose %d' % (i + 1))
        c = cols[i % len(cols)]
        pts = _dibujar_robot(ax, q, color=c, color_art=c, color_ef=c,
                             label=et, ejes=False, efector=True)
        todos.append(pts)
    ax.scatter(0, 0, 0, color='k', s=80, label='Base')
    ax.plot([], [], [], linestyle='None', marker='*', markersize=13,
            markerfacecolor='0.3', markeredgecolor='k', label='Efector')
    todos = np.vstack(todos)
    ax.set_title('Manipulador 4 GDL - %d poses' % len(poses))
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _iguales(ax, todos); ax.legend(); ax.view_init(elev=15, azim=-70)
    plt.tight_layout(); return fig


def plot_nube(nube, q_pose=None):
    fig = plt.figure(figsize=(7, 6)); ax = fig.add_subplot(111, projection='3d')
    ax.scatter(nube[:, 0], nube[:, 1], nube[:, 2], s=2, alpha=0.25,
               c=nube[:, 2], cmap='viridis')
    if q_pose is not None:
        pts, _ = cinematica_directa(q_pose)
        ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], '-o', color='red',
                linewidth=2.5, markersize=5, label='Robot')
        ax.legend()
    ax.set_title('Nube de puntos - espacio de trabajo (%d muestras)' % len(nube))
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _iguales(ax, nube); plt.tight_layout(); return fig


# ============================================================
#   5b) GUARDAR IMAGEN Y GIF
# ============================================================
def guardar_imagen(poses, ruta='robot4_pasos.png', dpi=150, nombres=None):
    """Guarda en un PNG las poses superpuestas (los 'pasos' del robot)."""
    fig = plot_robots(poses, nombres=nombres)
    fig.savefig(ruta, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print("Imagen guardada:", ruta)
    return ruta


def _trayectoria(poses, pasos=14, pausa=5, cerrar=True):
    """Interpola entre poses consecutivas (con una pausa en cada una)."""
    seq = [np.array(p, float) for p in poses]
    if cerrar:
        seq = seq + [seq[0]]          # vuelve a la primera -> GIF en bucle
    qs = []
    for a, b in zip(seq[:-1], seq[1:]):
        qs += [a] * pausa
        for t in np.linspace(0, 1, pasos, endpoint=False):
            qs.append(a + (b - a) * t)
    qs += [seq[-1]] * pausa
    return qs


def crear_gif(poses, ruta='robot4.gif', pasos=14, pausa=5,
              fps=20, dpi=90, girar=False):
    """
    GIF del robot moviendose por las poses (pasos).
      pasos : cuadros de transicion entre poses consecutivas
      pausa : cuadros quieto en cada pose
      girar : si True, la camara gira lentamente
    """
    qs = _trayectoria(poses, pasos, pausa)
    allp = np.vstack([cinematica_directa(q)[0] for q in qs])
    c = allp.mean(0); r = (allp.max(0) - allp.min(0)).max() / 2 or 1.0

    fig = plt.figure(figsize=(8, 7)); ax = fig.add_subplot(111, projection='3d')

    def update(k):
        ax.cla()
        _dibujar_robot(ax, qs[k], color='tab:blue', color_art='tab:blue',
                       color_ef='red', ejes=False, efector=True)
        ax.scatter(0, 0, 0, color='k', s=70)
        ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
        try: ax.set_box_aspect([1, 1, 1])
        except Exception: pass
        azim = -70 + (360 * k / len(qs) if girar else 0)
        ax.view_init(elev=15, azim=azim)
        ax.set_title('Manipulador 4 GDL - movimiento por poses')
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
        print("Pose %d - efector (x,y,z) [m]: %s" % (i + 1, np.round(pts[-1], 4)))

    # 1) Imagen con los 4 pasos superpuestos
    guardar_imagen(poses, 'Robot-Asignado/robot4_pasos.png')

    # 2) GIF del robot moviendose por los 4 pasos
    crear_gif(poses, 'Robot-Asignado/robot4.gif', girar=False)

    # (opcional) figuras en pantalla:
    # plot_ejes(Q_POSE); plot_robots(poses); plot_nube(nube_de_puntos(), q_pose=Q_POSE); plt.show()