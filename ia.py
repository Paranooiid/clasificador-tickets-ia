"""Clasificación de tickets: con un modelo local (Ollama) o con reglas simples."""

import json
import urllib.error
import urllib.request
from pathlib import Path

CATEGORIAS = ("hardware", "red", "perifericos", "software")
PRIORIDADES = ("alta", "media", "baja")

RUTA_PROMPT = Path(__file__).parent / "prompts" / "clasificar_ticket.txt"

# Esquema JSON que Ollama usa para forzar la forma de la respuesta.
ESQUEMA_RESPUESTA = {
    "type": "object",
    "properties": {
        "categoria": {"type": "string", "enum": list(CATEGORIAS)},
        "prioridad": {"type": "string", "enum": list(PRIORIDADES)},
        "solucion": {"type": "string"},
    },
    "required": ["categoria", "prioridad", "solucion"],
}


class ErrorClasificacion(Exception):
    pass


def validar(resultado):
    """Revisa que la respuesta del modelo tenga valores permitidos."""
    if not isinstance(resultado, dict):
        raise ErrorClasificacion(f"La respuesta no es un objeto JSON: {resultado!r}")
    categoria = str(resultado.get("categoria", "")).strip().lower()
    prioridad = str(resultado.get("prioridad", "")).strip().lower()
    solucion = str(resultado.get("solucion", "")).strip()
    categoria = categoria.replace("periféricos", "perifericos")
    if categoria not in CATEGORIAS:
        raise ErrorClasificacion(f"Categoría no válida: {categoria!r}")
    if prioridad not in PRIORIDADES:
        raise ErrorClasificacion(f"Prioridad no válida: {prioridad!r}")
    if not solucion:
        raise ErrorClasificacion("La solución sugerida está vacía")
    return {"categoria": categoria, "prioridad": prioridad, "solucion": solucion}


class ClasificadorOllama:
    """Llama a un modelo local con la API HTTP de Ollama (sin librerías externas)."""

    def __init__(self, modelo="llama3.2", url="http://localhost:11434", reintentos=2, timeout=120):
        self.modelo = modelo
        self.url = url.rstrip("/")
        self.reintentos = reintentos
        self.timeout = timeout
        self.prompt_sistema = RUTA_PROMPT.read_text(encoding="utf-8")
        self.nombre = f"ollama:{modelo}"

    def _llamar(self, descripcion):
        cuerpo = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": self.prompt_sistema},
                {"role": "user", "content": f'Ticket: "{descripcion}"'},
            ],
            "format": ESQUEMA_RESPUESTA,
            "stream": False,
            "options": {"temperature": 0},
        }
        peticion = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                datos = json.load(respuesta)
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", errors="replace")
            raise ErrorClasificacion(f"Ollama respondió {e.code}: {detalle}") from e
        except urllib.error.URLError as e:
            raise ErrorClasificacion(
                f"No se pudo conectar con Ollama en {self.url}. "
                "¿Está abierto? Prueba con: ollama serve"
            ) from e
        return datos["message"]["content"]

    def clasificar(self, descripcion):
        ultimo_error = None
        for _ in range(self.reintentos + 1):
            texto = self._llamar(descripcion)
            try:
                return validar(json.loads(texto))
            except (json.JSONDecodeError, ErrorClasificacion) as e:
                ultimo_error = e
        raise ErrorClasificacion(f"Respuesta inválida tras {self.reintentos + 1} intentos: {ultimo_error}")


class ClasificadorReglas:
    """Línea base sin IA: busca palabras clave. Sirve para probar sin Ollama y para comparar."""

    nombre = "reglas"

    PALABRAS = {
        "red": ["internet", "wifi", "red", "ping", "desconecta", "switch", "router", "cable de red"],
        "perifericos": ["mouse", "teclado", "tecla", "audífono", "audifono", "micrófono", "microfono",
                        "cámara", "camara", "control", "volante", "impresora", "bluetooth"],
        "software": ["windows", "steam", "epic", "battle.net", "juego", "driver", "antivirus",
                     "launcher", "sesión", "software", "instal", "league", "valorant", "fortnite"],
        "hardware": ["enciende", "apaga", "ventilador", "caliente", "disco", "monitor", "pantalla",
                     "fuente", "ram", "silla"],
    }
    URGENTE = ["ninguna", "varias", "todo el local", "no enciende", "caliente", "disco", "pantalla azul",
               "no imprime"]

    SOLUCIONES = {
        "red": "Revisar el cable de red y las luces del switch; reiniciar el adaptador de red del equipo.",
        "perifericos": "Probar el dispositivo en otro puerto o equipo y reemplazarlo por uno de repuesto si sigue fallando.",
        "software": "Reiniciar el programa, verificar actualizaciones y revisar los archivos del juego desde el launcher.",
        "hardware": "Apagar el equipo, revisar conexiones internas y temperatura, y probar con piezas de repuesto.",
    }

    def clasificar(self, descripcion):
        texto = descripcion.lower()
        categoria = "hardware"
        for cat, palabras in self.PALABRAS.items():
            if any(p in texto for p in palabras):
                categoria = cat
                break
        if any(p in texto for p in self.URGENTE):
            prioridad = "alta"
        elif categoria == "perifericos":
            prioridad = "baja"
        else:
            prioridad = "media"
        return {"categoria": categoria, "prioridad": prioridad, "solucion": self.SOLUCIONES[categoria]}
