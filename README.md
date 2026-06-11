# Tablero de Inversiones

Dashboard local en Flask para seguir una cartera de inversiones en pesos argentinos.

Actualmente incluye:

- Bitcoin (`BTC`)
- NVIDIA Corp (`NVDA`)
- Resumen general de cartera
- Cards por activo
- Tabla de posiciones
- Grafico de evolucion de cartera
- Grafico de composicion por tipo de activo
- Grafico realtime de Bitcoin via CoinGecko
- Grafico realtime de NVIDIA via Yahoo Finance convertido a ARS

## Ejecutar localmente

```bat
cd C:\Python\04_Proyectos\tablero_inversiones_demo
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python crear_db.py
python ingesta\actualizar_todo.py
python app.py
```

Abrir:

```text
http://127.0.0.1:5000
```

## Datos

Las operaciones viven en:

```text
data\operaciones\operaciones_demo.csv
```

Los precios base viven en:

```text
data\precios\precios_demo.csv
```

La base SQLite local es:

```text
inversiones.db
```

## Deploy en Vercel

El proyecto tiene:

- `app.py` con la app Flask expuesta como `app`
- `requirements.txt` con dependencias Python
- `.python-version` fijando Python 3.12
- `vercel.json` para excluir caches Python del bundle

En Vercel, importar el repositorio desde GitHub y desplegar con la configuracion por defecto.

Nota: esta app incluye datos de cartera. Usar repositorio privado y considerar proteger el deployment si no queres exponer esa informacion.
