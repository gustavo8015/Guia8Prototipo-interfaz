"""Reportes y gráficas (paso 5 de la arquitectura).

Escribe archivos CSV con los resultados y, si matplotlib está instalado,
tres gráficas en PNG. Sin matplotlib el prototipo funciona igual y solo
se omiten las imágenes.
"""
import csv
import os

from ventas_distribuido import top_productos

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def pesos(valor):
    """Formatea un entero como pesos colombianos: 1234567 -> $1.234.567"""
    return "$" + f"{valor:,}".replace(",", ".")


def _escribir_csv(ruta, encabezado, filas):
    # utf-8-sig para que Excel muestre bien las tildes.
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(encabezado)
        escritor.writerows(filas)


def guardar_reportes(resultado, parciales, carpeta="resultados"):
    """Guarda los reportes en CSV y devuelve la lista de archivos creados."""
    os.makedirs(carpeta, exist_ok=True)
    creados = []

    ciudades = sorted(resultado["ingresos_ciudad"].items(), key=lambda p: -p[1])
    ruta = os.path.join(carpeta, "ingresos_por_ciudad.csv")
    _escribir_csv(ruta, ["ciudad", "ingresos"], ciudades)
    creados.append(ruta)

    ruta = os.path.join(carpeta, "top5_productos.csv")
    _escribir_csv(ruta, ["producto", "unidades"], top_productos(resultado, 5))
    creados.append(ruta)

    meses = sorted(resultado["ingresos_mes"].items())
    ruta = os.path.join(carpeta, "ingresos_por_mes.csv")
    _escribir_csv(ruta, ["mes", "ingresos"], meses)
    creados.append(ruta)

    if parciales:
        # Una columna por partición y al final la suma consolidada.
        encabezado = ["ciudad"] + [f"particion_{p['particion']}" for p in parciales] + ["consolidado"]
        filas = []
        for ciudad, total in ciudades:
            fila = [ciudad] + [p["ingresos_ciudad"].get(ciudad, 0) for p in parciales] + [total]
            filas.append(fila)
        filas.append(["REGISTROS"] + [p["registros"] for p in parciales] + [resultado["registros"]])
        ruta = os.path.join(carpeta, "comparacion_particiones.csv")
        _escribir_csv(ruta, encabezado, filas)
        creados.append(ruta)

    creados += _graficas(resultado, carpeta)
    return creados


def _graficas(resultado, carpeta):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib no está instalado: se omiten las gráficas.")
        return []

    creados = []
    color = "#1f4e79"

    ciudades = sorted(resultado["ingresos_ciudad"].items(), key=lambda p: p[1])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh([c for c, _ in ciudades], [v / 1e6 for _, v in ciudades], color=color)
    ax.set_xlabel("Ingresos (millones de pesos)")
    ax.set_title("Ingresos por ciudad")
    fig.tight_layout()
    ruta = os.path.join(carpeta, "grafica_ingresos_ciudad.png")
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    creados.append(ruta)

    top = top_productos(resultado, 5)[::-1]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh([p for p, _ in top], [c for _, c in top], color=color)
    ax.set_xlabel("Unidades vendidas")
    ax.set_title("Cinco productos con más unidades vendidas")
    fig.tight_layout()
    ruta = os.path.join(carpeta, "grafica_top5_productos.png")
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    creados.append(ruta)

    meses = sorted(resultado["ingresos_mes"].items())
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([MESES[int(m[5:7]) - 1] for m, _ in meses], [v / 1e6 for _, v in meses], color=color)
    ax.set_ylabel("Ingresos (millones de pesos)")
    ax.set_title("Ingresos por mes")
    fig.tight_layout()
    ruta = os.path.join(carpeta, "grafica_ingresos_mes.png")
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    creados.append(ruta)
    return creados
