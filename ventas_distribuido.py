"""Fase 3. Procesamiento de ventas por particiones.

IMPORTANTE: esto es una SIMULACIÓN. Los "nodos" son procesos
independientes del sistema operativo que corren en el mismo computador;
no hay un clúster real ni comunicación por red.

El esquema sigue la idea de MapReduce:

1. particionar()        divide el archivo CSV en rangos de bytes.
2. procesar_rango()     es la tarea de cada nodo: lee solo su rango y
                        entrega totales parciales (etapa "map").
3. consolidar()         suma los parciales en un resultado único
                        (etapa "reduce").
4. ejecutar_distribuido() hace de coordinador: lanza los procesos, espera
                        los parciales, relanza la partición cuyo proceso
                        haya fallado y registra los tiempos.
"""
import json
import multiprocessing
import os
import shutil
import time


# Se usa el método "spawn" en todos los sistemas operativos: cada proceso
# arranca con un intérprete nuevo y sin memoria compartida con el
# coordinador. Es el método por defecto en Windows y, al fijarlo, los
# tiempos medidos en Linux o macOS son comparables.
mp = multiprocessing.get_context("spawn")


# --------------------------------------------------------------------------
# 1. Particionamiento
# --------------------------------------------------------------------------
def particionar(ruta, particiones):
    """Divide el archivo en `particiones` rangos de bytes (inicio, fin).

    Los cortes caen en cualquier byte, incluso a mitad de una línea. La
    regla que evita perder o duplicar ventas está en procesar_rango():
    cada línea pertenece a la partición en la que empieza.
    """
    tamano = os.path.getsize(ruta)
    paso = tamano // particiones
    rangos = []
    for i in range(particiones):
        inicio = i * paso
        fin = tamano if i == particiones - 1 else (i + 1) * paso
        rangos.append((inicio, fin))
    return rangos


# --------------------------------------------------------------------------
# 2. Tarea de cada nodo (map)
# --------------------------------------------------------------------------
def procesar_rango(ruta, inicio, fin):
    """Lee las ventas cuyo primer byte está en [inicio, fin) y las resume."""
    ingresos_ciudad = {}
    cantidad_producto = {}
    ingresos_mes = {}
    registros = 0

    with open(ruta, "rb") as archivo:
        if inicio == 0:
            archivo.readline()  # encabezado
        else:
            # Se retrocede un byte y se descarta hasta el fin de esa línea.
            # Si el corte cayó justo al comienzo de una línea, lo descartado
            # es solo el salto de línea anterior y no se pierde nada.
            archivo.seek(inicio - 1)
            archivo.readline()

        while archivo.tell() < fin:
            linea = archivo.readline()
            if not linea:
                break
            campos = linea.decode("utf-8").strip().split(",")
            if len(campos) != 6:
                continue  # línea vacía o dañada
            _, fecha, ciudad, producto, cantidad, precio = campos
            cantidad = int(cantidad)
            ingreso = cantidad * int(precio)
            mes = fecha[:7]  # AAAA-MM

            ingresos_ciudad[ciudad] = ingresos_ciudad.get(ciudad, 0) + ingreso
            cantidad_producto[producto] = cantidad_producto.get(producto, 0) + cantidad
            ingresos_mes[mes] = ingresos_mes.get(mes, 0) + ingreso
            registros += 1

    return {
        "registros": registros,
        "ingresos_ciudad": ingresos_ciudad,
        "cantidad_producto": cantidad_producto,
        "ingresos_mes": ingresos_mes,
    }


# --------------------------------------------------------------------------
# 3. Consolidación (reduce)
# --------------------------------------------------------------------------
def consolidar(parciales):
    """Suma los resultados parciales de todas las particiones."""
    total = {
        "registros": 0,
        "ingresos_ciudad": {},
        "cantidad_producto": {},
        "ingresos_mes": {},
    }
    for parcial in parciales:
        total["registros"] += parcial["registros"]
        for clave in ("ingresos_ciudad", "cantidad_producto", "ingresos_mes"):
            destino = total[clave]
            for nombre, valor in parcial[clave].items():
                destino[nombre] = destino.get(nombre, 0) + valor
    return total


def top_productos(resultado, n=5):
    """Los n productos con más unidades vendidas.

    Se calcula después de consolidar. Cada partición entrega el conteo de
    todos sus productos y no su propio "top 5", porque un producto puede
    quedar sexto en cada partición y aun así estar entre los cinco primeros
    del total.
    """
    pares = sorted(resultado["cantidad_producto"].items(), key=lambda p: (-p[1], p[0]))
    return pares[:n]


def ejecutar_secuencial(ruta):
    """Línea base: un solo proceso recorre el archivo completo."""
    inicio = time.perf_counter()
    resultado = procesar_rango(ruta, 0, os.path.getsize(ruta))
    return resultado, time.perf_counter() - inicio


# --------------------------------------------------------------------------
# 4. Nodos simulados y coordinador
# --------------------------------------------------------------------------
def _nodo(ruta, inicio, fin, indice, carpeta, fallar):
    """Código que ejecuta cada proceso trabajador."""
    t0 = time.perf_counter()
    parcial = procesar_rango(ruta, inicio, fin)
    if fallar:
        # Fallo simulado: el proceso muere después de trabajar y antes de
        # entregar su resultado, como un nodo que se apaga de repente.
        os._exit(1)
    parcial["particion"] = indice
    parcial["segundos"] = time.perf_counter() - t0
    # Se escribe en un archivo temporal y se renombra al final. Así el
    # coordinador nunca encuentra un parcial a medio escribir.
    destino = os.path.join(carpeta, f"parcial_{indice}.json")
    with open(destino + ".tmp", "w", encoding="utf-8") as archivo:
        json.dump(parcial, archivo, ensure_ascii=False)
    os.replace(destino + ".tmp", destino)


def ejecutar_distribuido(ruta, particiones, carpeta="parciales",
                         fallar_particion=None, max_reintentos=2):
    """Coordina el procesamiento por particiones.

    fallar_particion: índice de la partición cuyo proceso fallará en el
    primer intento (para la prueba de tolerancia a fallos).

    Devuelve (resultado, segundos, parciales, eventos).
    """
    inicio_total = time.perf_counter()
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta)
    os.makedirs(carpeta)

    rangos = particionar(ruta, particiones)
    eventos = []
    pendientes = list(range(particiones))
    intento = 0

    while pendientes:
        intento += 1
        if intento > max_reintentos + 1:
            raise RuntimeError(
                f"Las particiones {pendientes} no terminaron tras {max_reintentos} reintentos"
            )
        procesos = []
        for i in pendientes:
            fallar = (i == fallar_particion and intento == 1)
            proceso = mp.Process(
                target=_nodo,
                args=(ruta, rangos[i][0], rangos[i][1], i, carpeta, fallar),
            )
            proceso.start()
            procesos.append((i, proceso))

        fallidas = []
        for i, proceso in procesos:
            proceso.join()
            entregado = os.path.exists(os.path.join(carpeta, f"parcial_{i}.json"))
            if proceso.exitcode == 0 and entregado:
                eventos.append(f"intento {intento}: partición {i} entregó su resultado")
            else:
                eventos.append(
                    f"intento {intento}: partición {i} FALLÓ "
                    f"(código de salida {proceso.exitcode}); se vuelve a lanzar"
                )
                fallidas.append(i)
        pendientes = fallidas

    parciales = []
    for i in range(particiones):
        with open(os.path.join(carpeta, f"parcial_{i}.json"), encoding="utf-8") as archivo:
            parciales.append(json.load(archivo))

    resultado = consolidar(parciales)
    return resultado, time.perf_counter() - inicio_total, parciales, eventos


def mismos_resultados(a, b):
    """True si dos resultados coinciden en todos los totales."""
    claves = ("registros", "ingresos_ciudad", "cantidad_producto", "ingresos_mes")
    return all(a[c] == b[c] for c in claves)
