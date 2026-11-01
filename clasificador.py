"""Clasificador de tickets de soporte con IA.

Lee tickets desde un CSV, los clasifica (categoría, prioridad y solución sugerida)
con un modelo local de Ollama y guarda los resultados en SQLite.

Uso:
    python clasificador.py                      # clasifica data/tickets.csv con Ollama
    python clasificador.py --motor reglas       # sin IA, con palabras clave (para probar)
    python clasificador.py --probar "el mouse no responde"
    python clasificador.py --consultas          # muestra las consultas de consultas.sql
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import db
from ia import ClasificadorOllama, ClasificadorReglas, ErrorClasificacion

RAIZ = Path(__file__).parent
COLUMNAS_CSV = {"id", "fecha", "equipo", "descripcion"}


def leer_tickets(ruta_csv):
    # utf-8-sig acepta también los CSV guardados desde Excel (que agregan un BOM al inicio).
    with open(ruta_csv, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        faltantes = COLUMNAS_CSV - set(lector.fieldnames or [])
        if faltantes:
            sys.exit(f"Al CSV le faltan columnas: {', '.join(sorted(faltantes))}")
        return [fila for fila in lector if fila["descripcion"].strip()]


def imprimir_tabla(columnas, filas):
    if not filas:
        print("  (sin resultados)\n")
        return
    textos = [[str(v) for v in fila] for fila in filas]
    anchos = [min(60, max(len(c), *(len(f[i]) for f in textos))) for i, c in enumerate(columnas)]
    linea = lambda valores: "  " + " | ".join(v[:60].ljust(a) for v, a in zip(valores, anchos))
    print(linea(columnas))
    print("  " + "-+-".join("-" * a for a in anchos))
    for fila in textos:
        print(linea(fila))
    print()


def mostrar_consultas(con, ruta_sql):
    for titulo, sql in db.leer_consultas(ruta_sql):
        print(f"== {titulo} ==")
        imprimir_tabla(*db.ejecutar_consulta(con, sql))


def clasificar_csv(clasificador, con, tickets, reprocesar):
    ok, errores, omitidos = 0, 0, 0
    inicio = time.perf_counter()
    for ticket in tickets:
        if not reprocesar and db.ya_clasificado(con, ticket["id"]):
            omitidos += 1
            continue
        try:
            resultado = clasificador.clasificar(ticket["descripcion"])
        except ErrorClasificacion as e:
            errores += 1
            print(f"[{ticket['id']:>3}] ERROR: {e}")
            if "No se pudo conectar" in str(e):
                break
            continue
        db.guardar(con, ticket, resultado, clasificador.nombre)
        ok += 1
        print(f"[{ticket['id']:>3}] {resultado['categoria']:<11} {resultado['prioridad']:<5} "
              f"{ticket['descripcion'][:55]}")
    segundos = time.perf_counter() - inicio
    print(f"\nClasificados: {ok} | Errores: {errores} | Ya estaban: {omitidos} | Tiempo: {segundos:.1f} s")
    return errores == 0


def main():
    p = argparse.ArgumentParser(description="Clasificador de tickets de soporte con IA")
    p.add_argument("--csv", default=RAIZ / "data" / "tickets.csv", help="CSV de entrada")
    p.add_argument("--db", default=RAIZ / "tickets.db", help="Base de datos SQLite de salida")
    p.add_argument("--motor", choices=["ollama", "reglas"], default="ollama")
    p.add_argument("--modelo", default="llama3.2", help="Modelo de Ollama (ej. llama3.2, qwen2.5, mistral)")
    p.add_argument("--ollama-url", default="http://localhost:11434")
    p.add_argument("--reprocesar", action="store_true", help="Vuelve a clasificar tickets ya guardados")
    p.add_argument("--probar", metavar="TEXTO", help="Clasifica un solo ticket y lo muestra, sin guardar")
    p.add_argument("--consultas", action="store_true", help="Solo ejecuta las consultas de consultas.sql")
    args = p.parse_args()

    # La consola de Windows a veces no usa UTF-8; evita errores con tildes.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.motor == "ollama":
        clasificador = ClasificadorOllama(modelo=args.modelo, url=args.ollama_url)
    else:
        clasificador = ClasificadorReglas()

    if args.probar:
        try:
            r = clasificador.clasificar(args.probar)
        except ErrorClasificacion as e:
            sys.exit(f"ERROR: {e}")
        print(f"Categoría: {r['categoria']}\nPrioridad: {r['prioridad']}\nSolución:  {r['solucion']}")
        return

    con = db.conectar(args.db)
    try:
        if not args.consultas:
            tickets = leer_tickets(args.csv)
            print(f"Clasificando {len(tickets)} tickets con {clasificador.nombre}...\n")
            clasificar_csv(clasificador, con, tickets, args.reprocesar)
            print()
        mostrar_consultas(con, RAIZ / "consultas.sql")
    finally:
        con.close()


if __name__ == "__main__":
    main()
