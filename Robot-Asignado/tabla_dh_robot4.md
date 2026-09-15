# Asignación de ejes y tabla DH — Manipulador de 4 GDL

Primeramente, se observó el tipo de articulaciones del robot asignado, en este caso, todas son de rotación. De modo que para asignar los vectores base de cada eje articular, se tomó el eje Zᵢ para que la articulación rotara alrededor de este. Para esto, nos quedó de la siguiente manera.

> **Nota:** En el dibujo los ejes paralelos apuntan hacia afuera; los dibujé apuntando así un poco rotados para que se notaran, o si no serían solo puntos. El dibujo lo modifiqué utilizando draw.io

Primero, para Z1 tenemos un eje vertical ya que la articulación rota horizontalmente. Los demás ejes, como rotan verticalmente, los Z2, Z3 y Z4 quedaron paralelos, horizontales, salientes del dibujo.

Ahora bien, para los ejes Xᵢ, perpendiculares a Zᵢ y Zᵢ₋₁: el primero X1 se visualiza un poco rotado, pero este va hacia la izquierda, es por mejor visualización del dibujo, perpendicular a Z1 y Z2, de este modo queda positivo el ángulo. Luego tenemos X2, que está sobre el brazo apuntando hacia la derecha para mantener el ángulo positivo, y finalmente X3 nos queda hacia abajo sobre la "garra", también para mantener el ángulo positivo.

Una vez terminado esto, se agregó el sistema de referencia Z0 y X0. Z0 colineal a Z1, y X0 perpendicular a Z1 y Z0, hacia la izquierda por el signo positivo.

De aquí partimos para obtener, con lo visto en clase, la matriz de parámetros de DH, donde nos quedó:

## Tabla de parámetros DH (convención modificada de Craig)

| i | α₍ᵢ₋₁₎ | a₍ᵢ₋₁₎ | θᵢ | dᵢ | Tipo |
|:-:|:------:|:------:|:--:|:--:|:----:|
| 1 | 0 | 0 | **θ₁** | d₁ | Rotación |
| 2 | π/2 | 0 | **θ₂** | 0 | Rotación |
| 3 | 0 | a₂ | **θ₃** | 0 | Rotación |
| 4 | 0 | a₃ | **θ₄** | 0 | Rotación |

**Donde:**

- **θ₁, θ₂, θ₃, θ₄** — variables articulares (las 4 juntas son de rotación).
- **d₁** — altura de la base al hombro (a lo largo de Z1).
- **a₂** — longitud del brazo (hombro → codo).
- **a₃** — longitud del antebrazo (codo → muñeca).

**Justificación de cada fila:**

- **Fila 1 (J1, giro de base):** Z0 y Z1 son colineales (verticales) ⇒ α₀ = 0 y a₀ = 0; la altura de la base sube a lo largo de Z1 ⇒ d₁.
- **Fila 2 (J2, hombro):** Z1 (vertical) pasa a Z2 (horizontal) ⇒ α₁ = π/2; ambos ejes se cruzan en el hombro ⇒ a₁ = 0.
- **Fila 3 (J3, codo):** Z2 ∥ Z3 ⇒ α₂ = 0; la longitud del brazo va a lo largo de X2 ⇒ a₂.
- **Fila 4 (J4, muñeca):** Z3 ∥ Z4 ⇒ α₃ = 0; la longitud del antebrazo va a lo largo de X3 ⇒ a₃.

> El sentido positivo elegido para cada Xᵢ (X0 y X1 hacia la izquierda, X2 a la derecha, X3 hacia abajo) fija el signo/offset de cada variable articular, pero no cambia la geometría del robot.

## Transformaciones espaciales

Las **transformaciones homogéneas** son la herramienta estándar en robótica para
describir a la vez la **posición** y la **orientación** de un cuerpo, combinando
rotación y traslación en una sola matriz. Su ventaja es que permiten **encadenar
movimientos** simplemente multiplicando matrices.

Como el mBot2 se mueve sobre un plano, su **pose** se describe con tres valores:
posición `(x, y)` y orientación `θ`. La transformación homogénea en 2D es una
matriz 3×3:

$$
T = \begin{bmatrix} \cos\theta & -\sin\theta & x \\ \sin\theta & \cos\theta & y \\ 0 & 0 & 1 \end{bmatrix}
$$

- El bloque 2×2 superior izquierdo es la **rotación** del robot respecto al mundo.
- La última columna `(x, y)` es la **traslación** (posición del robot).
- La fila `(0, 0, 1)` es la que hace la matriz "homogénea" y unifica rotación y traslación.

Un punto expresado en el sistema de referencia del robot se lleva al sistema del
mundo multiplicándolo por `T` (en coordenadas homogéneas `[x, y, 1]ᵀ`). Una
secuencia de movimientos se compone multiplicando sus matrices:

$$ T_{total} = T_1 \cdot T_2 \cdot T_3 \cdots $$

En este proyecto, cada acción del robot (avanzar una distancia, girar un ángulo) se
puede ver como una transformación que **actualiza su pose** sobre la pista; el modo
pista corrige continuamente la orientación `θ` para mantener el robot alineado con
la línea.
