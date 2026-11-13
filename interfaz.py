"""Interfaz web local del prototipo.

Levanta un servidor en este mismo computador (solo biblioteca estándar) y
abre el navegador. Desde la página se elige el número de registros y de
particiones, se ejecuta el procesamiento y se ven los resultados.

Uso:
    python interfaz.py

Para cerrarla: Ctrl + C en la terminal.
"""
import json
import os
import statistics
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import generar_datos
import reportes
import ventas_distribuido as vd

CARPETA = os.path.dirname(os.path.abspath(__file__))
CANDADO = threading.Lock()  # una ejecución a la vez: comparten la carpeta de parciales
MAX_REGISTROS = 2_000_000
MAX_PARTICIONES = 16
# Únicos archivos que el servidor entrega además de la página.
ESTATICOS = {
    "/vendor/three.module.min.js": ("vendor/three.module.min.js", "text/javascript; charset=utf-8"),
}


def _archivo(registros):
    ruta = os.path.join("datos", f"ventas_{registros}.csv")
    if not os.path.exists(ruta):
        generar_datos.generar(ruta, registros)
    return ruta


def _entero(datos, clave, minimo, maximo):
    try:
        valor = int(datos[clave])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Falta el valor de «{clave}» o no es un número entero.")
    if not minimo <= valor <= maximo:
        raise ValueError(f"«{clave}» debe estar entre {minimo} y {maximo}.")
    return valor


def ejecutar(datos):
    registros = _entero(datos, "registros", 100, MAX_REGISTROS)
    particiones = _entero(datos, "particiones", 1, MAX_PARTICIONES)
    fallar = datos.get("fallar")
    if fallar is not None:
        fallar = _entero(datos, "fallar", 0, particiones - 1)

    ruta = _archivo(registros)
    secuencial, t_s = vd.ejecutar_secuencial(ruta)
    resultado, t_p, parciales, eventos = vd.ejecutar_distribuido(
        ruta, particiones, fallar_particion=fallar)
    reportes.guardar_reportes(resultado, parciales)

    return {
        "archivo": ruta.replace("\\", "/"),
        "tamano_mb": round(os.path.getsize(ruta) / 1048576, 2),
        "registros": resultado["registros"],
        "particiones": particiones,
        "t_secuencial": t_s,
        "t_particiones": t_p,
        "aceleracion": t_s / t_p,
        "coincide": vd.mismos_resultados(secuencial, resultado),
        "eventos": eventos,
        "parciales": [
            {"particion": p["particion"], "registros": p["registros"], "segundos": p["segundos"],
             "ingresos": sum(p["ingresos_ciudad"].values())}
            for p in parciales
        ],
        "ciudades": sorted(resultado["ingresos_ciudad"].items(), key=lambda x: -x[1]),
        "top": vd.top_productos(resultado, 5),
        "meses": sorted(resultado["ingresos_mes"].items()),
        "nucleos": os.cpu_count(),
    }


def rendimiento(datos):
    tamanos = datos.get("tamanos") or [10000, 100000, 500000]
    tamanos = [_entero({"registros": n}, "registros", 100, MAX_REGISTROS) for n in tamanos][:4]
    particiones = _entero(datos, "particiones", 2, MAX_PARTICIONES)
    repeticiones = 3
    filas = []
    for n in tamanos:
        ruta = _archivo(n)
        tiempos = []
        for _ in range(repeticiones):
            referencia, t = vd.ejecutar_secuencial(ruta)
            tiempos.append(t)
        t_s = statistics.median(tiempos)
        tiempos, coincide = [], True
        for _ in range(repeticiones):
            r, t, _, _ = vd.ejecutar_distribuido(ruta, particiones)
            tiempos.append(t)
            coincide = coincide and vd.mismos_resultados(r, referencia)
        t_p = statistics.median(tiempos)
        filas.append({"registros": n, "t_secuencial": t_s, "t_particiones": t_p,
                      "aceleracion": t_s / t_p, "coincide": coincide})
    return {"filas": filas, "particiones": particiones, "repeticiones": repeticiones,
            "nucleos": os.cpu_count()}


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # sin ruido en la terminal

    def _responder(self, codigo, cuerpo, tipo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(CARPETA, "interfaz.html"), "rb") as archivo:
                self._responder(200, archivo.read(), "text/html; charset=utf-8")
        elif self.path in ESTATICOS:
            ruta, tipo = ESTATICOS[self.path]
            with open(os.path.join(CARPETA, ruta), "rb") as archivo:
                self._responder(200, archivo.read(), tipo)
        else:
            self._responder(404, b"No encontrado", "text/plain; charset=utf-8")

    def do_POST(self):
        acciones = {"/api/ejecutar": ejecutar, "/api/rendimiento": rendimiento}
        accion = acciones.get(self.path)
        if accion is None:
            self._responder(404, b"{}", "application/json")
            return
        try:
            largo = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(largo) or b"{}")
            with CANDADO:
                respuesta, codigo = accion(datos), 200
        except ValueError as error:
            respuesta, codigo = {"error": str(error)}, 400
        except Exception as error:  # se informa en la página en vez de cortar la conexión
            respuesta, codigo = {"error": f"No se pudo completar la ejecución: {error}"}, 500
        cuerpo = json.dumps(respuesta, ensure_ascii=False).encode("utf-8")
        self._responder(codigo, cuerpo, "application/json; charset=utf-8")


def main():
    os.chdir(CARPETA)  # datos/, parciales/ y resultados/ quedan junto a los scripts
    servidor = None
    for puerto in range(8000, 8011):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
            break
        except OSError:
            continue
    if servidor is None:
        raise SystemExit("No hay un puerto libre entre 8000 y 8010.")
    url = f"http://127.0.0.1:{puerto}"
    print(f"Interfaz disponible en {url}")
    print("Para cerrarla presione Ctrl + C en esta ventana.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nInterfaz cerrada.")


if __name__ == "__main__":
    main()
