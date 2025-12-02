import os
import json
import asyncio
import websockets
from telegram import Bot

# === CONFIGURACIÓN ===
WS_URL = "wss://livetiming.alkamelsystems.com/socket/websocket"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "@GPdeMadrid"

bot = Bot(TELEGRAM_TOKEN)

# === DICCIONARIO DE PILOTOS (rellénalo con los dorsales reales FE) ===
PILOTOS = {
    "51": "Nico Müller",
    "94": "Pascal Wehrlein",
    "9": "Mitch Evans",
    "13": "António Félix da Costa",
    "1": "Oliver Rowland",
    "23": "Norman Nato",
    "21": "Nyck de Vries",
    "48": "Edoardo Mortara",
    "7": "Maximilian Günther",
    "77": "Taylor Barnard",
    "27": "Jake Dennis",
    "28": "Felipe Drugovich",
    "14": "Joel Eriksson",
    "16": "Sébastien Buemi",
    "3": "Pepe Martí",
    "33": "Dan Ticktum",
    "11": "Lucas di Grassi",
    "22": "Zane Maloney",
    "25": "Jean-Éric Vergne",
    "37": "Nick Cassidy"
}

def nombre_piloto(dorsal):
    return PILOTOS.get(dorsal, "Piloto Secreto")


# === PROCESAR MENSAJES DEL WEBSOCKET ===
async def procesar_mensaje(msg):
    obj = json.loads(msg)

    if obj.get("collection") != "standings":
        return None
    
    standings_dict = obj["fields"]["standings"]["standings"]

    # Convertir standings en lista ordenada por posición
    lista = []

    for pos_str, datos in standings_dict.items():
        # extraer el campo data
        raw = datos.get("data", "")
        partes = raw.split(";")

        if len(partes) < 2:
            continue
        
        try:
            position = int(partes[0])
        except:
            continue

        dorsal = partes[1]

        lista.append((position, dorsal))

    # ordenar por posición real
    lista.sort(key=lambda x: x[0])

    # top 4
    top4 = lista[:4]

    texto = "🏁 *TOP 4 EN VIVO*\n\n"

    for pos, dorsal in top4:
        texto += f"*{pos}. {nombre_piloto(dorsal)}* — #{dorsal}\n"

    return texto


# === ESCUCHAR WEBSOCKET ===
async def escuchar_websocket():
    async with websockets.connect(WS_URL) as ws:
        # primer saludo requerido por Meteor/AlKamel
        await ws.send(json.dumps({"msg": "connect", "version": "1", "support": ["1"]}))
        
        publicado = ""

        while True:
            msg = await ws.recv()

            texto = await procesar_mensaje(msg)

            if texto and texto != publicado:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=texto,
                    parse_mode="Markdown"
                )
                publicado = texto


# === MAIN ===
if __name__ == "__main__":
    asyncio.run(escuchar_websocket())


