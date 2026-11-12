from datetime import datetime, timezone, timedelta
import hashlib
import os
import re
from bs4 import BeautifulSoup
import requests

URL = "https://winningpc.com/itop-vpn-coupon-code-free-license-key-vip-account/"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
if not NTFY_TOPIC:
    raise ValueError("Falta configurar el secreto NTFY_TOPIC en Settings > Secrets and variables > Actions")
HASH_FILE = "ultimo_estado.txt"




def calcular_tiempo_transcurrido(fecha_dt):
    if fecha_dt.tzinfo is None:
        fecha_dt = fecha_dt.replace(tzinfo=ZONA_PERU)
    ahora = datetime.now(ZONA_PERU)
    diferencia = ahora - fecha_dt.astimezone(ZONA_PERU)
    segundos_totales = int(diferencia.total_seconds())

    if segundos_totales < 0:
        return "hoy mismo"

    horas_totales = round(segundos_totales / 3600, 1)
    if horas_totales < 24:
        return f"hace {horas_totales} horas"
    else:
        dias = int(horas_totales // 24)
        horas_restantes = round(horas_totales % 24, 1)
        return f"hace {dias} día(s) y {horas_restantes} horas"


def analizar_pagina():
    resp = requests.get(URL, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    texto_completo = " ".join(soup.get_text(" ", strip=True).split())

    # 1. Extraer la fecha exacta de "Verified" en "At a glance" (ej. "Verified Nov 11, 2026")
    match_verified = re.search(
        r"Verified\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4})",
        texto_completo,
    )
    if not match_verified:
        match_verified = re.search(
            r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4})\b",
            texto_completo,
        )

    if match_verified:
        fecha_str = match_verified.group(1).replace(".", "")
        tiempo_texto = fecha_str
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                fecha_dt = datetime.strptime(fecha_str, fmt)
                tiempo_texto = f"{fecha_str} ({calcular_tiempo_transcurrido(fecha_dt)})"
                break
            except ValueError:
                continue
    else:
        fecha_str = "sin-fecha"
        tiempo_texto = "fecha no detectada"

    # 2. Extraer el estado del giveaway (Active/Expired) y el bloque de "License codes" / "Official giveaway"
    estado_giveaway = "Active" if "Official giveaway Active" in texto_completo else "Revisar estado"

    bloque_licencia = ""
    match_bloque = re.search(
        r"(Official giveaway.*?Official publisher link)",
        texto_completo,
    )
    if match_bloque:
        bloque_licencia = match_bloque.group(1)
    else:
        # Respaldo: capturar alrededor de "License codes"
        match_codigos = re.search(r"(License codes.{0,300})", texto_completo)
        bloque_licencia = match_codigos.group(1) if match_codigos else ""

    # 3. Buscar cualquier correo VIP o clave oculta en el HTML del contenedor de códigos
    datos_ocultos = []
    for tag in soup.find_all(attrs={"data-code": True}):
        datos_ocultos.append(tag["data-code"])
    for tag in soup.find_all(attrs={"data-clipboard-text": True}):
        datos_ocultos.append(tag["data-clipboard-text"])

    firma_unica = f"{fecha_str}|{estado_giveaway}|{bloque_licencia}|{'-'.join(datos_ocultos)}"
    hash_actual = hashlib.sha256(firma_unica.encode("utf-8")).hexdigest()

    return hash_actual, tiempo_texto, estado_giveaway


def enviar_notificacion(tiempo_texto, estado_giveaway):
    mensaje = (
        f"¡Actualización en iTop VPN ({estado_giveaway})!\n"
        f"Verified: {tiempo_texto}.\n"
        "Toca aquí para abrir la página y revelar la cuenta VIP."
    )
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=mensaje.encode("utf-8"),
        headers={
            "Title": "Nueva licencia iTop VPN",
            "Priority": "urgent",
            "Tags": "key,rotating_light",
            "Click": URL,
        },
        timeout=15,
    ).raise_for_status()


def main():
    hash_actual, tiempo_texto, estado_giveaway = analizar_pagina()
    hash_anterior = ""

    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            hash_anterior = f.read().strip()

    if hash_actual != hash_anterior:
        with open(HASH_FILE, "w", encoding="utf-8") as f:
            f.write(hash_actual)
        enviar_notificacion(tiempo_texto, estado_giveaway)
        print(f"Notificación enviada. Verified: {tiempo_texto}")
    else:
        print(f"Sin cambios. Sigue en: {tiempo_texto}")


if __name__ == "__main__":
    main()
