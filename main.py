"""Ejecución completa del prototipo sobre un conjunto de datos.

Genera el CSV si no existe, lo procesa de forma secuencial y por
particiones, compara ambos resultados y guarda los reportes.

Uso:
    python main.py
    python main.py --registros 500000 --particiones 4
    python main.py --registros 100000 --particiones 4 --fallar 2
"""
import argparse
import os

import generar_datos
import reportes
import ventas_distribuido as vd


def main():
    parser = argparse.ArgumentParser(description="Análisis de ventas por particiones (simulación).")
    parser.add_argument("--registros", type=int, default=100000)
    parser.add_argument("--particiones", type=int, default=4)
    parser.add_argument("--fallar", type=int, default=None, metavar="N",
                        help="simula la caída del proceso de la partición N en el primer intento")
    args = parser.parse_args()

    ruta = os.path.join("datos", f"ventas_{args.registros}.csv")
    if not os.path.exists(ruta):
        print(f"Generando {args.registros} ventas sintéticas...")
        generar_datos.generar(ruta, args.registros)

    print(f"\nFuente de datos: {ruta} ({os.path.getsize(ruta) / 1048576:.2f} MB)")
    print("Nota: los nodos son procesos del mismo equipo (simulación, no clúster real).\n")

    secuencial, t_s = vd.ejecutar_secuencial(ruta)
    print(f"Secuencial (1 proceso):          {t_s:.3f} s")

    distribuido, t_p, parciales, eventos = vd.ejecutar_distribuido(
        ruta, args.particiones, fallar_particion=args.fallar)
    print(f"Por particiones ({args.particiones} procesos):    {t_p:.3f} s")
    print(f"Aceleración Ts/Tp:               {t_s / t_p:.2f}\n")

    print("Registro del coordinador:")
    for evento in eventos:
        print("  " + evento)

    print("\nRegistros por partición:")
    for p in parciales:
        print(f"  partición {p['particion']}: {p['registros']:>8} registros en {p['segundos']:.3f} s")
    print(f"  consolidado: {distribuido['registros']:>8} registros")

    iguales = vd.mismos_resultados(secuencial, distribuido)
    print(f"\n¿El consolidado coincide con el secuencial? {'SÍ' if iguales else 'NO'}")

    print("\nIngresos por ciudad:")
    for ciudad, valor in sorted(distribuido["ingresos_ciudad"].items(), key=lambda p: -p[1]):
        print(f"  {ciudad:<14}{reportes.pesos(valor):>20}")

    print("\nCinco productos con más unidades vendidas:")
    for i, (producto, unidades) in enumerate(vd.top_productos(distribuido, 5), 1):
        print(f"  {i}. {producto:<26}{unidades:>8}")

    print("\nIngresos por mes:")
    for mes, valor in sorted(distribuido["ingresos_mes"].items()):
        print(f"  {mes}  {reportes.pesos(valor):>20}")

    creados = reportes.guardar_reportes(distribuido, parciales)
    print("\nReportes guardados:")
    for archivo in creados:
        print("  " + archivo)


if __name__ == "__main__":
    main()
