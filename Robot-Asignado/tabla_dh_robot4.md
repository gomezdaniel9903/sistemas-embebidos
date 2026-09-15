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

## Transformaciones espaciales (transformaciones homogéneas)

En robótica, una **transformación homogénea** es una matriz de **4×4** que describe, con un solo objeto, la **posición** *y* la **orientación** de un sistema de referencia respecto a otro. Su ventaja es que permite **encadenar** varios movimientos (una articulación tras otra) simplemente **multiplicando matrices**, lo cual es la base del método de Denavit-Hartenberg.

### Coordenadas homogéneas

Un punto del espacio (x, y, z) se escribe agregándole un 1:

    p = [x, y, z, 1]ᵀ

Ese "1" extra es lo que permite incluir la **traslación** dentro de una multiplicación de matrices: una rotación por sí sola no puede trasladar, pero en coordenadas homogéneas rotación y traslación se combinan en una sola operación.

### Estructura de la matriz

Una transformación homogénea junta una rotación y una traslación:

    T = | R   p |        R = rotación (3×3, la orientación)
        | 0   1 |        p = traslación (3×1, la posición del origen)

En forma completa:

    | r11  r12  r13  px |
    | r21  r22  r23  py |
    | r31  r32  r33  pz |
    |  0    0    0    1 |

Al aplicarla a un punto, **p′ = T · p**, el punto queda rotado y trasladado del sistema de origen al de destino.

### Composición (por qué son útiles)

Si `⁰T₁` lleva del sistema 0 al 1, y `¹T₂` del 1 al 2, entonces del 0 al 2:

    ⁰T₂ = ⁰T₁ · ¹T₂

Encadenando así **todas** las articulaciones se obtiene la **cinemática directa**:

    ⁰Tₙ = ⁰T₁ · ¹T₂ · … · ⁿ⁻¹Tₙ

La **posición del efector final** es la columna de traslación (p) de `⁰Tₙ`, y su **orientación** es la submatriz R.

### Relación con Denavit-Hartenberg

Cada fila de la tabla DH define una transformación homogénea entre dos sistemas consecutivos (mediante la matriz DH). Al multiplicar esas matrices en orden se obtiene la pose del efector final — que es exactamente lo que calcula el código de cinemática directa.

> **Dato útil:** la inversa de una transformación homogénea (que "deshace" el movimiento) es
> `T⁻¹ = | Rᵀ  −Rᵀp ; 0  1 |`, sin necesidad de invertir la matriz completa de 4×4.
