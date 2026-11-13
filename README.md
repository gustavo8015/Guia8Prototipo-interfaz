# Guía 8. Procesamiento distribuido de datos (prototipo)

Análisis de ventas por particiones en Python. Es una **simulación**: los
"nodos" son procesos independientes que corren en el mismo computador,
no un clúster real.

## Requisitos

- Python 3.10 o superior (no hay que instalar nada más para ejecutar).
- Opcional, solo para las gráficas: `pip install matplotlib`

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `generar_datos.py` | Fase 1. Crea el CSV de ventas sintéticas. |
| `ventas_distribuido.py` | Fase 3. Particiona, procesa, consolida y recupera fallos. |
| `reportes.py` | Reportes en CSV y gráficas en PNG. |
| `main.py` | Corre todo el flujo con un archivo y muestra los resultados. |
| `pruebas_rendimiento.py` | Fase 4. Mide tiempos y calcula la aceleración. |
| `test_ventas.py` | Nueve pruebas automáticas. |
| `interfaz.py` e `interfaz.html` | Interfaz web local para ejecutar el prototipo desde el navegador. |

## Interfaz gráfica

```
python interfaz.py
```

Se abre el navegador en http://127.0.0.1:8000. Allí se eligen los
registros y las particiones y se puede simular la caída de un proceso.
Una escena 3D reproduce la ejecución real (particionamiento, lectura de
cada nodo, fallo y relanzamiento, consolidación) y debajo aparecen los
tiempos, los parciales, el registro del coordinador y las gráficas.

- La escena se dibuja con Three.js, incluido en la carpeta `vendor`
  (licencia MIT); no necesita internet.
- La animación se reproduce después de medir: mientras el servidor
  procesa, la escena queda quieta para no alterar los tiempos.
- La terminal debe quedar abierta mientras se usa; se cierra con Ctrl + C.

## Cómo ejecutarlo (PowerShell o terminal)

```
cd Guia8Prototipo-interfaz

# 1. Pruebas automáticas
python -m unittest -v test_ventas.py

# 2. Flujo completo con 100.000 ventas y 4 particiones
python main.py --registros 100000 --particiones 4

# 3. Lo mismo, pero el proceso de la partición 2 falla en el primer intento
python main.py --registros 500000 --particiones 4 --fallar 2

# 4. Pruebas de rendimiento (10.000, 100.000 y 500.000 registros)
python pruebas_rendimiento.py

# 4b. Con el archivo adicional de 2.000.000 de registros
python pruebas_rendimiento.py --tamanos 10000 100000 500000 2000000
```

Los archivos de datos se crean solos en `datos/` la primera vez. Los
resultados quedan en `resultados/`:

- `tiempos.csv` y `grafica_tiempos.png`: tiempos y aceleración.
- `entorno.txt`: características del equipo donde se corrió la prueba.
- `ingresos_por_ciudad.csv`, `top5_productos.csv`, `ingresos_por_mes.csv`.
- `comparacion_particiones.csv`: parcial de cada partición y consolidado.

La carpeta `parciales/` guarda el resultado que entregó cada proceso
(`parcial_0.json`, `parcial_1.json`, ...).

## Nota sobre los tiempos

Los tiempos del informe se midieron en un equipo Linux con 2 núcleos
lógicos. En otro computador los valores cambian: al ejecutar
`pruebas_rendimiento.py` se generan de nuevo `tiempos.csv` y
`entorno.txt` con los datos de ese equipo.
