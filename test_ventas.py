"""Pruebas automáticas del prototipo.

Uso:
    python -m unittest -v test_ventas.py
"""
import os
import shutil
import tempfile
import unittest

import generar_datos
import ventas_distribuido as vd


class PruebasVentas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carpeta = tempfile.mkdtemp(prefix="guia8_")
        cls.ruta = os.path.join(cls.carpeta, "ventas.csv")
        generar_datos.generar(cls.ruta, 5000, semilla=7)
        cls.esperado, _ = vd.ejecutar_secuencial(cls.ruta)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.carpeta, ignore_errors=True)

    def _parciales(self):
        return os.path.join(self.carpeta, "parciales")

    def test_archivo_pequeno_calculado_a_mano(self):
        ruta = os.path.join(self.carpeta, "mini.csv")
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(generar_datos.ENCABEZADO + "\n")
            f.write("1,2025-01-10,Bogotá,Mouse óptico,2,45000\n")
            f.write("2,2025-01-15,Cali,Cable HDMI,3,25000\n")
            f.write("3,2025-02-01,Bogotá,Cable HDMI,1,25000\n")
        r, _ = vd.ejecutar_secuencial(ruta)
        self.assertEqual(r["registros"], 3)
        self.assertEqual(r["ingresos_ciudad"], {"Bogotá": 115000, "Cali": 75000})
        self.assertEqual(r["cantidad_producto"], {"Mouse óptico": 2, "Cable HDMI": 4})
        self.assertEqual(r["ingresos_mes"], {"2025-01": 165000, "2025-02": 25000})
        self.assertEqual(vd.top_productos(r, 1), [("Cable HDMI", 4)])

    def test_generador_es_repetible(self):
        otra = os.path.join(self.carpeta, "ventas_b.csv")
        generar_datos.generar(otra, 5000, semilla=7)
        with open(self.ruta, "rb") as a, open(otra, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_secuencial_cuenta_todos_los_registros(self):
        self.assertEqual(self.esperado["registros"], 5000)
        self.assertEqual(len(self.esperado["ingresos_mes"]), 12)

    def test_los_rangos_cubren_el_archivo_sin_huecos(self):
        rangos = vd.particionar(self.ruta, 7)
        self.assertEqual(rangos[0][0], 0)
        self.assertEqual(rangos[-1][1], os.path.getsize(self.ruta))
        for (_, fin), (inicio, _) in zip(rangos, rangos[1:]):
            self.assertEqual(fin, inicio)

    def test_ninguna_venta_se_pierde_ni_se_duplica(self):
        # Sin procesos: se comprueba solo la regla de corte de líneas.
        for n in (1, 2, 3, 4, 7, 16, 50):
            partes = [vd.procesar_rango(self.ruta, a, b)
                      for a, b in vd.particionar(self.ruta, n)]
            total = vd.consolidar(partes)
            self.assertTrue(vd.mismos_resultados(total, self.esperado), f"{n} particiones")

    def test_distribuido_coincide_con_secuencial(self):
        for n in (2, 4):
            r, _, parciales, _ = vd.ejecutar_distribuido(self.ruta, n, self._parciales())
            self.assertEqual(len(parciales), n)
            self.assertTrue(vd.mismos_resultados(r, self.esperado))

    def test_top_5_ordenado_de_mayor_a_menor(self):
        top = vd.top_productos(self.esperado, 5)
        self.assertEqual(len(top), 5)
        cantidades = [c for _, c in top]
        self.assertEqual(cantidades, sorted(cantidades, reverse=True))

    def test_fallo_de_un_proceso_se_recupera(self):
        r, _, _, eventos = vd.ejecutar_distribuido(
            self.ruta, 4, self._parciales(), fallar_particion=2)
        self.assertTrue(any("FALLÓ" in e for e in eventos))
        self.assertTrue(vd.mismos_resultados(r, self.esperado))

    def test_fallo_sin_reintentos_se_informa(self):
        with self.assertRaises(RuntimeError):
            vd.ejecutar_distribuido(self.ruta, 4, self._parciales(),
                                    fallar_particion=1, max_reintentos=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
