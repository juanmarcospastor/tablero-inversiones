from datetime import datetime

import pandas as pd
import requests


def obtener_precio_bitcoin_coingecko():
    """
    Trae el precio actual de Bitcoin en ARS y USD desde CoinGecko.
    Devuelve un DataFrame compatible con la tabla precios del proyecto.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "ars,usd"
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    fecha = datetime.now().strftime("%Y-%m-%d")

    return pd.DataFrame([
        {
            "fecha": fecha,
            "ticker": "BTC",
            "precio": float(data["bitcoin"]["ars"]),
            "moneda": "ARS",
            "fuente": "CoinGecko"
        },
        {
            "fecha": fecha,
            "ticker": "BTC_USD",
            "precio": float(data["bitcoin"]["usd"]),
            "moneda": "USD",
            "fuente": "CoinGecko"
        }
    ])


if __name__ == "__main__":
    print(obtener_precio_bitcoin_coingecko())
