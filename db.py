"""Persistencia en SQLite: tickets, sus clasificaciones y consultas de negocio."""

import re
import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY,
    fecha       TEXT NOT NULL,
    equipo      TEXT NOT NULL,
    descripcion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clasificaciones (
    ticket_id     INTEGER PRIMARY KEY REFERENCES tickets(id),
    categoria     TEXT NOT NULL CHECK (categoria IN ('hardware', 'red', 'perifericos', 'software')),
    prioridad     TEXT NOT NULL CHECK (prioridad IN ('alta', 'media', 'baja')),
    solucion      TEXT NOT NULL,
    motor         TEXT NOT NULL,
    clasificado_en TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def conectar(ruta):
    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def guardar(con, ticket, resultado, motor):
    """Guarda (o reemplaza) un ticket y su clasificación."""
    with con:
        con.execute(
            """INSERT INTO tickets (id, fecha, equipo, descripcion) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   fecha = excluded.fecha, equipo = excluded.equipo, descripcion = excluded.descripcion""",
            (int(ticket["id"]), ticket["fecha"], ticket["equipo"], ticket["descripcion"]),
        )
        con.execute(
            """INSERT INTO clasificaciones (ticket_id, categoria, prioridad, solucion, motor)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(ticket_id) DO UPDATE SET
                   categoria = excluded.categoria, prioridad = excluded.prioridad,
                   solucion = excluded.solucion, motor = excluded.motor,
                   clasificado_en = datetime('now', 'localtime')""",
            (int(ticket["id"]), resultado["categoria"], resultado["prioridad"], resultado["solucion"], motor),
        )


def ya_clasificado(con, ticket_id):
    fila = con.execute("SELECT 1 FROM clasificaciones WHERE ticket_id = ?", (int(ticket_id),)).fetchone()
    return fila is not None


def leer_consultas(ruta_sql):
    """Lee consultas.sql: cada consulta termina en ';' y su título es la primera línea '-- '."""
    texto = Path(ruta_sql).read_text(encoding="utf-8")
    consultas = []
    for bloque in texto.split(";"):
        bloque = bloque.strip()
        if not bloque:
            continue
        titulo = re.search(r"^--\s*(.+)$", bloque, re.MULTILINE)
        consultas.append((titulo.group(1) if titulo else "Consulta", bloque))
    return consultas


def ejecutar_consulta(con, sql):
    cursor = con.execute(sql)
    columnas = [c[0] for c in cursor.description]
    return columnas, cursor.fetchall()
