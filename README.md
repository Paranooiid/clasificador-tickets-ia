# Clasificador de tickets de soporte con IA

**Clasifica automáticamente tickets de soporte técnico por categoría y prioridad, sugiere una primera solución y guarda todo en SQL**, para que el técnico sepa qué atender primero.

Basado en problemas reales que atendí en el soporte de un local gamer (Gameclub): mouse que no responde, cámaras sin imagen, PCs que se apagan, el local sin internet…

## Ejemplo

**Entrada** (`data/tickets.csv`):

```csv
id,fecha,equipo,descripcion
4,2026-10-02,RECEPCION,No hay internet en ninguna máquina del local
1,2026-10-01,PC-01,El mouse no responde aunque está conectado
```

**Salida** (guardada en la tabla `clasificaciones` de `tickets.db`; la solución es un ejemplo, el texto exacto depende del modelo):

| ticket | categoría | prioridad | solución sugerida |
|---|---|---|---|
| 4 | red | alta | Revisar que el router y el switch principal estén encendidos y reiniciarlos; comprobar si el proveedor tiene caída. |
| 1 | perifericos | baja | Probar el mouse en otro puerto USB y reemplazarlo por uno de repuesto si sigue sin responder. |

**Consulta de negocio** (de `consultas.sql`): tickets por categoría y prioridad

```
categoria   | alta | media | baja | total
------------+------+-------+------+------
perifericos | ...  | ...   | ...  | ...
```

> 📸 Tip: reemplaza esta sección con una captura de tu terminal después de ejecutarlo.

## Tecnologías

- **Python** (solo biblioteca estándar: `csv`, `sqlite3`, `urllib`, `argparse`)
- **IA** con un modelo de lenguaje local y gratuito vía **Ollama** (por defecto `llama3.2`)
- **Prompt engineering**: prompt con criterios de categoría y prioridad, ejemplos (few-shot) y salida en JSON validada con un esquema
- **SQL** con **SQLite**: dos tablas relacionadas, restricciones `CHECK` y consultas con `JOIN`, `GROUP BY` y `HAVING`
- **Automatización de procesos**: procesa el CSV completo, reintenta respuestas inválidas y no repite tickets ya clasificados

## Cómo ejecutarlo

1. Instala [Python 3.9+](https://www.python.org/downloads/) y [Ollama](https://ollama.com/download).
2. Descarga el modelo:
   ```bash
   ollama pull llama3.2
   ```
3. Clasifica los tickets y ve las consultas:
   ```bash
   python clasificador.py
   ```
4. (Opcional) Prueba un ticket a mano, o ejecuta sin IA con reglas de palabras clave:
   ```bash
   python clasificador.py --probar "la cámara no muestra imagen"
   ```
   ```bash
   python clasificador.py --motor reglas --reprocesar
   ```

Otras opciones: `--modelo qwen2.5`, `--csv otro.csv`, `--db otra.db`, `--consultas` (solo muestra las consultas), `--reprocesar`.

## Estructura

```
clasificador.py               Script principal (lee CSV, clasifica, guarda, muestra consultas)
ia.py                         Llamada a Ollama, validación de la respuesta y clasificador por reglas
db.py                         Esquema SQLite y guardado
prompts/clasificar_ticket.txt Prompt del modelo
consultas.sql                 Consultas de negocio
data/tickets.csv              30 tickets de ejemplo
```

## Qué aprendí y qué mejoraría

- **El prompt importa más que el código.** Definir con ejemplos qué es prioridad "alta" (afecta a varios equipos o hay riesgo de daño) hizo las respuestas mucho más consistentes que solo pedir "asigna una prioridad".
- **No confiar en la salida del modelo.** Pedir JSON con un esquema y validar los valores antes de guardarlos evita datos basura en la base de datos.
- **Comparar con una línea base.** El clasificador por palabras clave se equivoca en casos como "el software de *control* de tiempo" (lo marca como periférico); la IA entiende el contexto.
- **Mejoras:** medir la precisión contra tickets etiquetados a mano, guardar el historial de clasificaciones por modelo para compararlos, probar MySQL y hacer un pequeño panel web con los resultados.
