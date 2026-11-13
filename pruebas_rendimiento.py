"""Fase 4. Pruebas de rendimiento.

Para cada tamaño de archivo mide el tiempo secuencial y el tiempo por
particiones, repite cada medición varias veces, toma la mediana y calcula
la aceleración Ts/Tp. También comprueba que el resultado consolidado sea
igual al secuencial. Deja todo en la carpeta resultados/.

Uso:
    python pruebas_rendimiento.py
    python pruebas_rendimiento.py --tamanos 10000 100000 500000 --particiones 2 4 --repeticiones 5
"""
import argparse
import csv
import os
import platform
import statistics
import sys

import generar_datos
import ventas_distribuido as vd


def describir_entorno():
    lineas = [
        f"Sistema operativo: {platform.system()} {platform.release()}",
        f"Arquitectura: {platform.machine()}",
        f"Procesador: {platform.processor() or 'no informado por el sistema'}",
        f"Núcleos lógicos disponibles: {os.cpu_count()}",
        f"Python: {sys.version.split()[0]}",
        "Método de creación de procesos: spawn",
    ]
    try:  # memoria RAM, solo si el sistema la informa de esta manera
        paginas = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        lineas.append(f"Memoria RAM: {paginas / 1024 ** 3:.1f} GB")
    except (ValueError, OSError, AttributeError):
        pass
    return lineas


def main():
    parser = argparse.ArgumentParser(description="Pruebas de rendimiento del prototipo.")
    parser.add_argument("--tamanos", type=int, nargs="+", default=[10000, 100000, 500000])
    parser.add_argument("--particiones", type=int, nargs="+", default=[2, 4])
    parser.add_argument("--repeticiones", type=int, default=5)
    args = parser.parse_args()

    os.makedirs("resultados", exist_ok=True)
    entorno = describir_entorno()
    with open(os.path.join("resultados", "entorno.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(entorno) + "\n")
    print("\n".join(entorno))

    filas = []
    for n in args.tamanos:
        ruta = os.path.join("datos", f"ventas_{n}.csv")
        if not os.path.exists(ruta):
            generar_datos.generar(ruta, n)
        mb = os.path.getsize(ruta) / 1048576

        tiempos = []
        for _ in range(args.repeticiones):
            referencia, t = vd.ejecutar_secuencial(ruta)
            tiempos.append(t)
        t_s = statistics.median(tiempos)
        filas.append([n, f"{mb:.2f}", "secuencial", 1, f"{t_s:.3f}", "1.00", "referencia"])
        print(f"\n{n} registros ({mb:.2f} MB)")
        print(f"  secuencial        Ts = {t_s:.3f} s")

        for p in args.particiones:
            tiempos = []
            coincide = True
            for _ in range(args.repeticiones):
                resultado, t, _, _ = vd.ejecutar_distribuido(ruta, p)
                tiempos.append(t)
                coincide = coincide and vd.mismos_resultados(resultado, referencia)
            t_p = statistics.median(tiempos)
            filas.append([n, f"{mb:.2f}", "particiones", p, f"{t_p:.3f}",
                          f"{t_s / t_p:.2f}", "sí" if coincide else "NO"])
            print(f"  {p} particiones     Tp = {t_p:.3f} s   aceleración = {t_s / t_p:.2f}"
                  f"   resultado igual al secuencial: {'sí' if coincide else 'NO'}")

    ruta_csv = os.path.join("resultados", "tiempos.csv")
    with open(ruta_csv, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["registros", "tamano_mb", "modo", "procesos",
                           "segundos_mediana", "aceleracion", "coincide_con_secuencial"])
        escritor.writerows(filas)
    print(f"\nTiempos guardados en {ruta_csv}")
    _grafica(filas)


def _grafica(filas):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    tamanos = sorted({f[0] for f in filas})
    modos = []
    for f in filas:
        etiqueta = "Secuencial" if f[2] == "secuencial" else f"{f[3]} particiones"
        if etiqueta not in modos:
            modos.append(etiqueta)
    colores = ["#7f7f7f", "#1f4e79", "#c55a11", "#548235", "#7030a0"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ancho = 0.8 / len(modos)
    for j, modo in enumerate(modos):
        valores = []
        for n in tamanos:
            for f in filas:
                etiqueta = "Secuencial" if f[2] == "secuencial" else f"{f[3]} particiones"
                if f[0] == n and etiqueta == modo:
                    valores.append(float(f[4]))
        posiciones = [i + j * ancho for i in range(len(tamanos))]
        barras = ax.bar(posiciones, valores, ancho, label=modo, color=colores[j % len(colores)])
        ax.bar_label(barras, fmt="%.2f", fontsize=8, padding=2)
    ax.set_xticks([i + ancho * (len(modos) - 1) / 2 for i in range(len(tamanos))])
    ax.set_xticklabels([f"{n:,}".replace(",", ".") + " registros" for n in tamanos])
    ax.set_ylabel("Tiempo (segundos, mediana)")
    ax.set_title("Tiempo de ejecución según el tamaño del archivo")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join("resultados", "grafica_tiempos.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
