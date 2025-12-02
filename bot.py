import os
import json
import asyncio
import websockets
import time
from telegram import Bot

# --------------------------
#  TABLA DE PILOTOS
# --------------------------
PILOTOS = {
    51: {"nombre": "Nico Müller", "siglas": "MÜL"},
    94: {"nombre": "Pascal Wehrlein", "siglas": "WEH"},
    9:  {"nombre": "Mitch Evans", "siglas": "EVA"},
    13: {"nombre": "António Félix da Costa", "siglas": "DAC"},
    1:  {"nombre": "Oliver Rowland", "siglas": "ROW"},
    23: {"nombre": "Norman Nato", "siglas": "NAT"},
    21: {"nombre": "Nyck de Vries", "siglas": "DEV"},
    48: {"nombre": "Edoardo Mortara", "siglas": "MOR"},
    7:  {"nombre": "Maximilian Günther", "siglas": "GÜN"},
    77: {"nombre": "Taylor Barnard", "siglas": "BAR"},
    27: {"nombre": "Jake Dennis", "siglas": "DEN"},
    28: {"nombre": "Felipe Drugovich", "siglas": "DRU"},
    14: {"nombre": "Joel Eriksson", "siglas": "ERI"},
    16: {"nombre": "Sébastien Buemi", "siglas": "BUE"},
    3:  {"nombre": "Pepe Martí", "siglas": "MAR"},
    33: {"nombre": "Dan Ticktum", "siglas": "TIC"},
    11: {"nombre": "Lucas di Grassi", "siglas": "DIG"},
    22: {"nombre": "Zane Maloney", "siglas": "MAL"},
    25: {"nombre": "Jean-Éric Vergne", "siglas": "JEV"},
    37: {"nombre": "Nick Cassidy", "siglas": "CAS"},
}

def obtener_piloto(dorsal):
    dorsal = int(dorsal)
    if dorsal in PILOTOS:
        return PILOTOS[dorsal]["nombre"], PILOTOS[dorsal]["siglas"]
    return "Piloto Secreto", "???"

# --------------------------
#  TELEGRAM
# --------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(BOT_TOKEN)

# --------------------------
#  WEBSOCKET URL
# --------------------------
WS_URL = os.getenv("WS_URL")

ultimo_envio = 0


async def publicar_top4(dorsales):
    msg = "🏁 *TOP 4 en vivo*\n\n"

    for pos in range(1, 5):
        dorsal = dorsales[pos - 1] if pos <= len(dorsales) else None

        if not dorsal:
            msg += f"{pos}. — Sin datos\n"
            continue

        nombre, siglas = obtener_piloto(dorsal)
        msg += f"*{pos}.* #{dorsal} ({siglas}) — {nombre}\n"

    msg += "\nSuscríbete en: t.me/FormulaEEsp"

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=msg,
        parse_mode="Markdown"
    )


async def procesar_websocket():
    """Solo procesa mensajes que incluyen standings reales"""
    global ultimo_envio

    while True:
        try:
            print("🔌 Conectando al websocket...")
            async with websockets.connect(WS_URL) as ws:
                print("🟢 Conectado")

                async for message in ws:
                    try:
                        data = json.loads(message)
                    except:
                        continue

                    # --------------------------
                    #  FILTRAR SOLO "Standings"
                    # --------------------------
                    if "Standings" not in data:
                        continue

                    standings = data["Standings"]

                    if "Classification" not in standings:
                        continue

                    clasificacion = standings["Classification"]  # Lista de coches

                    # Ordenar por posición
                    clasificacion = sorted(clasificacion, key=lambda c: c.get("Position", 999))

                    dorsales_top4 = [car.get("RacingNumber") for car in clasificacion[:4]]

                    ahora = time.time()
                    if ahora - ultimo_envio >= 5:
                        await publicar_top4(dorsales_top4)
                        ultimo_envio = ahora

        except Exception as e:
            print("⚠ Error, reconectando en 3s:", e)
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(procesar_websocket())

