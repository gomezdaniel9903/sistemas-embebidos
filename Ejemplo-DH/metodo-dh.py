# -*- coding: utf-8 -*-
"""
Cinemática directa por Denavit-Hartenberg — convención MODIFICADA (Craig).
Manipulador de 5 GDL (Eje 1 prismático, Ejes 2-5 de revolución).
Genera la gráfica del robot y la nube de puntos (espacio de trabajo) en 3D.

Autor: (tu nombre)
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (habilita la proyección 3D)


# ============================================================
#   1) TABLA DE PARÁMETROS DH — convención MODIFICADA (Craig)
# ============================================================
# Columnas:  [ alpha_{i-1},  a_{i-1},  theta_i,  d_i,  sigma_i ]
#   alpha_{i-1} -> giro alrededor de X_{i-1}          [rad]
#   a_{i-1}     -> traslación a lo largo de X_{i-1}    [m]
#   theta_i     -> giro alrededor de Z_i              [rad]
#   d_i         -> traslación a lo largo de Z_i        [m]
#   sigma_i     -> 0 = REVOLUCIÓN (la variable es theta_i)
#                  1 = PRISMÁTICA (la variable es d_i)
#
#   * El valor que pongas en la columna variable (theta si 'R', d si 'P')
#     se usa como OFFSET y se le suma la variable de la junta q[i].
#     Aquí los offsets valen 0.
#   * Ángulos en RADIANES. Longitudes en METROS.
#
#   Valores tomados de la tabla del caso de estudio (5-GDL):
DH = [
    # alpha_{i-1},  a_{i-1},  theta_i,   d_i,    sigma
    [ np.pi/2,      0.00,     np.pi/2,   0.00,   1],   # Eje 1 - PRISMATICA (variable d1)
    [ 0.0,          0.33,     0.0,       0.00,   0],   # Eje 2 - revolucion (variable th2)
    [ 0.0,          0.40,     0.0,       0.00,   0],   # Eje 3 - revolucion (variable th3)
    [ np.pi/2,      0.00,     0.0,       0.16,   0],   # Eje 4 - revolucion (variable th4)
    [-np.pi/2,      0.00,     0.0,       0.00,   0],   # Eje 5 - revolucion (variable th5)
]

# Configuracion ("pose") en la que se DIBUJA el robot.
# Es el valor de la VARIABLE de cada junta: d1 en metros, th2..th5 en radianes.
Q_POSE = [0.10,               # d1  [m]  (junta prismatica)
          np.deg2rad(30),     # th2
          np.deg2rad(-45),    # th3
          np.deg2rad(60),     # th4
          np.deg2rad(0)]      # th5

Q_POSE_2 = [0.05,               # d1  [m]  (junta prismatica)
          np.deg2rad(80),     # th2
          np.deg2rad(-35),    # th3
          np.deg2rad(60),     # th4
          -np.deg2rad(180)]      # th5

Q_POSE_3 = [-0.1,               # d1  [m]  (junta prismatica)
          np.deg2rad(50),     # th2
          np.deg2rad(-25),    # th3
          np.deg2rad(60),     # th4
          np.deg2rad(0)]      # th5

Q_POSE_4 = [-0.2,               # d1  [m]  (junta prismatica)
          np.deg2rad(40),     # th2
          np.deg2rad(-15),    # th3
          np.deg2rad(60),     # th4
          -np.deg2rad(180)]      # th5



# ============================================================
#   2) MATRIZ DE TRANSFORMACION DH MODIFICADA (Craig)
# ============================================================
def dh_matrix(alpha, a, theta, d):
    """
    Matriz homogenea 4x4 de una articulacion (convencion DH MODIFICADA):
        T = Rot_x(alpha) . Trans_x(a) . Rot_z(theta) . Trans_z(d)
    """
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
    """
    Devuelve:
      puntos : array (n+1, 3) con la posicion del origen de cada sistema de
               referencia (incluye la base en el origen).
      frames : lista de matrices 4x4 (una por sistema, incluida la base).
    """
    T = np.eye(4)
    puntos = [T[:3, 3].copy()]
    frames = [T.copy()]

    for i, (alpha, a, theta, d, sigma) in enumerate(dh):
        if sigma == 0:            # revolucion -> la variable es theta
            theta = theta + q[i]
        else:                     # prismatica -> la variable es d
            d = d + q[i]
        T = T @ dh_matrix(alpha, a, theta, d)
        puntos.append(T[:3, 3].copy())
        frames.append(T.copy())

    return np.array(puntos), frames


# ============================================================
#   5) VISUALIZACION
# ============================================================
def _ejes_iguales(ax, pts):
    """Escala los 3 ejes por igual para que la geometria no se deforme."""
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
    """Dibuja los ejes X(rojo) Y(verde) Z(azul) de un sistema de referencia."""
    o = T[:3, 3]
    x, y, z = T[:3, 0], T[:3, 1], T[:3, 2]
    ax.quiver(*o, *x, length=escala, color='r', linewidth=1.2)
    ax.quiver(*o, *y, length=escala, color='g', linewidth=1.2)
    ax.quiver(*o, *z, length=escala, color='b', linewidth=1.2)
 
 
def _dibujar_robot(ax, q, dh=DH, color='0.2', label=None, mostrar_ejes=False,
                   efector=True, color_ef=None, label_ef=None, aprox=False):
    """
    Dibuja UN robot en la pose q sobre unos ejes 3D ya existentes (ax).
    No fija limites/titulo/leyenda: de eso se encarga quien llama.
      efector : marca el efector final (ultimo sistema) con una estrella.
      aprox   : dibuja ademas el vector de aproximacion (eje Z del efector).
    Devuelve los puntos (para poder escalar los ejes despues).
    """
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
        #ef_e = ef * np.array([1, -1, 1])
        c = color_ef if color_ef is not None else color
        ax.scatter(*ef, color=c, marker='*', s=180, edgecolors='k',
                   linewidths=0.7, depthshade=False, zorder=6, label=label_ef)
        # ax.scatter(*ef_e, color=c, marker='*', s=180, edgecolors='k',
        #                    linewidths=0.7, depthshade=False, zorder=6, label=label_ef)
        if aprox:                      # vector de aproximacion = eje Z del efector
            tam = np.linalg.norm(puntos.max(axis=0) - puntos.min(axis=0))
            escala = 0.18 * (tam if tam > 0 else 1.0)
            z = frames[-1][:3, 2]
            ax.quiver(*ef, *z, length=escala, color=c, linewidth=2)
            # ax.quiver(*ef_e, *z, length=escala, color=c, linewidth=2)
    return puntos
 
 
def plot_robot(q, dh=DH, mostrar_ejes=True, aprox=True):
    """Dibuja UNA sola pose del robot en su propia figura."""
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
    """
    Dibuja VARIAS poses del robot en la MISMA grafica 3D.
      poses   : lista de configuraciones, p.ej. [Q_POSE, Q_POSE_2, ...]
      nombres : lista opcional de etiquetas para la leyenda
    """
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection='3d')
 
    colores = plt.cm.tab10.colors          # 10 colores bien diferenciados
    todos = []
    for i, q in enumerate(poses):
        etiqueta = nombres[i] if nombres else ('Pose %d' % (i + 1))
        pts = _dibujar_robot(ax, q, dh, color=colores[i % len(colores)],
                             label=etiqueta, mostrar_ejes=mostrar_ejes,
                             efector=True)
        todos.append(pts)
 
    ax.scatter(0, 0, 0, color='k', s=70, label='Base')   # base comun
    ax.plot([], [], [], linestyle='None', marker='*', markersize=13,
            markerfacecolor='0.3', markeredgecolor='k',
            label='Efector final')                        # leyenda de la estrella
 
    todos = np.vstack(todos)               # escala usando TODAS las poses
    ax.set_title('Manipulador 5 GDL - %d poses' % len(poses))
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    _ejes_iguales(ax, todos)
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
#   6) PROGRAMA PRINCIPAL
# ============================================================
if __name__ == '__main__':
    puntos, _ = cinematica_directa(Q_POSE)
    print("Posicion del efector final (x, y, z) [m]:", np.round(puntos[-1], 4))

    # 1) Robot en la pose Q_POSE
    poses = [Q_POSE, Q_POSE_2, Q_POSE_3, Q_POSE_4]
 
    for i, q in enumerate(poses):
        pts, _ = cinematica_directa(q)
        print("Pose %d - efector final (x,y,z) [m]: %s" % (i + 1, np.round(pts[-1], 4)))
 
    # TODAS las poses en la MISMA grafica (pon mostrar_ejes=True para ver los sistemas):
    plot_robots(poses, mostrar_ejes=False)

    plt.show()