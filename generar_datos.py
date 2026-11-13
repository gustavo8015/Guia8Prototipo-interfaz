"""Fase 1. Generador de ventas sintéticas.

Crea un archivo CSV con los campos id_venta, fecha, ciudad, producto,
cantidad y precio_unitario. Los datos son inventados: no hay clientes,
documentos ni ningún dato personal. Con la misma semilla y el mismo
número de registros el archivo resultante siempre es idéntico, de modo
que las pruebas se pueden repetir.

Uso:
    python generar_datos.py --registros 10000
    python generar_datos.py --registros 500000 --salida datos/ventas_500000.csv
"""
import argparse
import os
import random
from datetime import date, timedelta

ENCABEZADO = "id_venta,fecha,ciudad,producto,cantidad,precio_unitario"

# Ciudad y peso relativo dentro del total de ventas.
CIUDADES = [
    ("Bogotá", 30),
    ("Medellín", 18),
    ("Cali", 14),
    ("Barranquilla", 10),
    ("Cartagena", 8),
    ("Bucaramanga", 8),
    ("Pereira", 6),
    ("Cúcuta", 6),
]

# Producto, precio unitario en pesos colombianos y peso relativo.
PRODUCTOS = [
    ("Audífonos inalámbricos", 120000, 14),
    ("Memoria USB 64 GB", 35000, 16),
    ("Mouse óptico", 45000, 13),
    ("Teclado mecánico", 180000, 8),
    ("Cargador rápido", 60000, 12),
    ("Cable HDMI", 25000, 11),
    ("Parlante Bluetooth", 150000, 7),
    ("Disco SSD 480 GB", 210000, 5),
    ("Cámara web HD", 130000, 4),
    ("Monitor 24 pulgadas", 620000, 3),
    ("Impresora multifuncional", 540000, 2),
    ("Tableta 10 pulgadas", 780000, 5),
]

# Peso de cada mes (enero a diciembre). Junio, noviembre y diciembre
# concentran más ventas para que el análisis mensual tenga algo que mostrar.
PESO_MES = [7, 6, 7, 7, 8, 10, 8, 8, 7, 8, 11, 13]

ANIO = 2025


def _fechas_y_pesos():
    """Devuelve todas las fechas del año y el peso de cada una."""
    fechas, pesos = [], []
    dia = date(ANIO, 1, 1)
    while dia.year == ANIO:
        fechas.append(dia.isoformat())
        pesos.append(PESO_MES[dia.month - 1])
        dia += timedelta(days=1)
    return fechas, pesos


def generar(ruta, registros, semilla=2026):
    """Escribe `registros` ventas en `ruta` y devuelve la ruta."""
    azar = random.Random(semilla)
    fechas, pesos_fecha = _fechas_y_pesos()
    ciudades = [c for c, _ in CIUDADES]
    pesos_ciudad = [p for _, p in CIUDADES]
    pesos_producto = [p for _, _, p in PRODUCTOS]
    indices_producto = list(range(len(PRODUCTOS)))

    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    # newline="\n" fija el fin de línea para que el archivo tenga los mismos
    # bytes en Windows y en Linux.
    with open(ruta, "w", encoding="utf-8", newline="\n") as archivo:
        archivo.write(ENCABEZADO + "\n")
        bloque = 50000
        escritos = 0
        while escritos < registros:
            n = min(bloque, registros - escritos)
            f = azar.choices(fechas, weights=pesos_fecha, k=n)
            c = azar.choices(ciudades, weights=pesos_ciudad, k=n)
            p = azar.choices(indices_producto, weights=pesos_producto, k=n)
            lineas = []
            for i in range(n):
                nombre, precio, _ = PRODUCTOS[p[i]]
                cantidad = azar.randint(1, 5)
                lineas.append(
                    f"{escritos + i + 1},{f[i]},{c[i]},{nombre},{cantidad},{precio}"
                )
            archivo.write("\n".join(lineas) + "\n")
            escritos += n
    return ruta


def main():
    parser = argparse.ArgumentParser(description="Genera ventas sintéticas en CSV.")
    parser.add_argument("--registros", type=int, default=10000)
    parser.add_argument("--salida", default=None)
    parser.add_argument("--semilla", type=int, default=2026)
    args = parser.parse_args()
    salida = args.salida or os.path.join("datos", f"ventas_{args.registros}.csv")
    generar(salida, args.registros, args.semilla)
    tamano = os.path.getsize(salida) / (1024 * 1024)
    print(f"Archivo creado: {salida} ({args.registros} registros, {tamano:.2f} MB)")


if __name__ == "__main__":
    main()
