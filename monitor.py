from datetime import datetime, timezone
import hashlib
import os
from bs4 import BeautifulSoup
import requests

URL = "https://winningpc.com/itop-vpn-coupon-code-free-license-key-vip-account/"
NTFY_TOPIC = "itop-vpn-alerta-9482"  # <-- Pon aquí tu tema secreto de ntfy
HASH_FILE = "ultimo_estado.txt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def calcular_tiempo_transcurrido(fecha_iso):
    fecha_pub = datetime.fromisoformat(fecha_iso).astimezone(timezone.utc)
    ahora = datetime.now(timezone.utc)
    diferencia = ahora - fecha_pub
    segundos_totales = int(diferencia.total_seconds())

    if segundos_totales < 0:
        return "recién publicado"

    horas_totales = round(segundos_totales / 3600, 1)
    if horas_totales < 24:
        return f"hace {horas_totales} horas"
    else:
        dias = int(horas_totales // 24)
        horas_restantes = round(horas_totales % 24, 1)
        return f"hace {dias} día(s) y {horas_restantes} horas (total: {horas_totales} h)"


def analizar_pagina():
    resp = requests.get(URL, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Extrae solo el contenido principal del artículo (ignora anuncios laterales)
    articulo = soup.find("div", class_="entry-content")
    texto = articulo.get_text(" ", strip=True) if articulo else resp.text
    hash_actual = hashlib.sha256(texto.encode("utf-8")).hexdigest()

    # Busca la fecha exacta de actualización o publicación en la página
    meta_fecha = soup.find("meta", property="article:modified_time") or soup.find(
        "meta", property="article:published_time"
    )

    if meta_fecha and meta_fecha.get("content"):
        tiempo_texto = calcular_tiempo_transcurrido(meta_fecha["content"])
    else:
        tiempo_texto = "fecha exacta no especificada en la web"

    return hash_actual, tiempo_texto


def enviar_notificacion(tiempo_texto):
    mensaje = (
        "¡Nueva licencia o actualización de iTop VPN detectada!\n"
        f"Publicado/Actualizado: {tiempo_texto}.\n"
        "Toca aquí para abrir la página y copiar la clave."
    )
    resp = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=mensaje.encode("utf-8"),
        headers={
            "Title": "Licencia iTop VPN disponible",
            "Priority": "urgent",
            "Tags": "key,rotating_light",
            "Click": URL,
        },
        timeout=15,
    )
    resp.raise_for_status()


def main():
    hash_actual, tiempo_texto = analizar_pagina()
    hash_anterior = ""

    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            hash_anterior = f.read().strip()

    # Notifica la primera vez (prueba inicial) y cada vez que publiquen algo nuevo
    if hash_actual != hash_anterior:
        with open(HASH_FILE, "w", encoding="utf-8") as f:
            f.write(hash_actual)
        enviar_notificacion(tiempo_texto)
        print(f"Notificación enviada. Estado: {tiempo_texto}")
    else:
        print(f"Sin cambios nuevos. Última actualización fue {tiempo_texto}.")


if __name__ == "__main__":
    main()
