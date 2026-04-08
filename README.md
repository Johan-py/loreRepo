# Author Consistency Analyzer
## v2.3
Herramienta de análisis de repositorios Git que evalúa la **consistencia de los commits por autor** a partir del historial del repositorio.

El programa clona un repositorio, extrae los commits y calcula métricas de consistencia para cada desarrollador.
El resultado es un **reporte ordenado por consistencia** que permite identificar patrones de trabajo en el equipo.

---

# Requisitos

La **única dependencia externa es Git**.

El script utiliza el comando `git log` para extraer la información del repositorio.

Verificar que Git esté instalado:

```bash
git --version
```

Si el comando devuelve la versión de Git, el sistema está listo para usar la herramienta.

No se requieren integraciones con servicios externos.

---

# Qué hace la herramienta

El analizador realiza los siguientes pasos:

1. Clona el repositorio en modo **bare**.
2. Extrae el historial de commits usando `git log`.
3. Procesa los commits y genera un dataset con:

   * autor
   * fecha
   * mensaje
   * líneas añadidas
   * líneas eliminadas
4. Calcula métricas de consistencia por desarrollador.
5. Genera un **reporte de ranking de autores**.

---

# Métricas evaluadas

El sistema calcula un **consistency score** basado en cuatro dimensiones.

## 1. Consistencia de mensajes de commit

Evalúa si el desarrollador utiliza **Conventional Commits**.

Se consideran válidos los commits que comienzan con:

```
feat
fix
docs
refactor
test
chore
```

Ejemplo:

```
feat: add authentication
fix: resolve login bug
docs: update README
```

El valor representa el porcentaje de commits que siguen este estándar.

---

## 2. Consistencia del tamaño de commits

Mide qué tan similares son los tamaños de los commits.

Se calcula la **desviación estándar** de las líneas modificadas:

```
changes = added + deleted
```

Un desarrollador que hace commits de tamaño relativamente constante obtiene mayor puntuación.

---

## 3. Consistencia temporal

Analiza la distribución de commits por día.

Desarrolladores que hacen commits de forma **regular en el tiempo** obtienen una puntuación más alta que quienes concentran muchos commits en un solo día.

---

## 4. Granularidad de commits

Penaliza commits demasiado grandes.

Se consideran commits grandes aquellos que modifican más de:

```
500 líneas
```

Mientras mayor sea la proporción de commits pequeños y enfocados, mayor será la puntuación.

---

# Cálculo del Consistency Score

Las métricas se combinan en una puntuación final:

```
consistency_score =
0.35 * message_consistency +
0.25 * size_consistency +
0.20 * frequency_consistency +
0.20 * granularity_consistency
```

El score final se normaliza en el rango:

```
0.0 – 1.0
```

Interpretación aproximada:

| Score       | Interpretación        |
| ----------- | --------------------- |
| 0.80 – 1.00 | Muy consistente       |
| 0.60 – 0.79 | Consistencia moderada |
| 0.40 – 0.59 | Irregular             |
| < 0.40      | Baja consistencia     |

Los autores con menos de **100 líneas modificadas en total** se excluyen del ranking para evitar ruido estadístico.

---

# Uso

Ejecutar el script principal:

```bash
python app.py
```

El programa solicitará o recibirá la URL de un repositorio Git.

Ejemplo:

```
https://github.com/user/project.git
```

---

# Salida

El analizador genera un archivo:

```
data/author_consistency_report.csv
```

Ejemplo de salida:

| author | total_commits | total_lines_changed | frequency_consistency | consistency_score |
| ------ | ------------- | ------------------- | --------------------- | ----------------- |
| Johan  | 25            | 1800                | 0.71                  | 0.82              |
| Maria  | 19            | 1300                | 0.65                  | 0.76              |
| Carlos | 12            | 900                 | 0.52                  | 0.63              |

El reporte está **ordenado por consistencia**.

---

# Limitaciones

* El análisis se basa únicamente en el historial de Git.
* No evalúa calidad del código ni revisiones de pull requests.
* El score mide **consistencia en el estilo de commits**, no productividad absoluta.

---

# Casos de uso

Esta herramienta puede utilizarse para:

* análisis de patrones de commits
* estudios de ingeniería de software
* métricas de actividad en repositorios
* soporte para herramientas de DevOps o ChatOps
* generación de reportes de actividad por desarrollador

---

# Licencia

Uso académico y experimental.
