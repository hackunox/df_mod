#!/usr/bin/env python
"""
Narrador DF – Narrador en tiempo real para Dwarf Fortress
Autor: hackuno
Licencia: MIT
"""
from __future__ import annotations

import argparse
import time
import tomllib
from collections import Counter, deque
from pathlib import Path
from typing import Deque, List, Optional

import openai
import pyttsx3

# ---------- Configuración y utilidades ---------- #

def cargar_config(ruta_cfg: Path):
    with ruta_cfg.open("rb") as f:
        cfg = tomllib.load(f)

    openai.api_key = cfg["openai"]["api_key"]
    return cfg


def leer_nuevas_lineas(fh) -> List[str]:
    """Devuelve las líneas añadidas desde la última llamada."""
    where = fh.tell()
    lineas = fh.readlines()
    if not lineas:
        fh.seek(where)
    return [l.decode("utf-8", errors="ignore").strip() for l in lineas]


def resumir_eventos(eventos: List[str], modelo: str, temp: float, max_tokens: int) -> str:
    """Usa OpenAI para filtrar, resumir y narrar."""
    system_prompt = (
        "Eres un narrador épico de Dwarf Fortress. "
        "Filtra líneas repetidas o irrelevantes, resume eventos similares, "
        "y genera una narración inmersiva en español neutro. "
        "Cuando detectes un error recurrente (p.ej. falta de materiales), "
        "sugiere una solución plausible dentro del juego."
    )
    user_content = "\n".join(eventos)
    respuesta = openai.ChatCompletion.create(
        model=modelo,
        temperature=temp,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return respuesta.choices[0].message.content.strip()


def hablar(texto: str, motor: pyttsx3.Engine, voice_id: str, rate: int):
    motor.setProperty("voice", voice_id)
    motor.setProperty("rate", rate)
    motor.say(texto)
    motor.runAndWait()


# ---------- Lógica principal ---------- #

def run(cfg):
    ruta_log = Path(cfg["gamelog"]["path"]).expanduser()
    if not ruta_log.exists():
        raise FileNotFoundError(f"No se encontró gamelog.txt en {ruta_log}")

    motor = pyttsx3.init(driverName=cfg["voice"]["engine"])
    voice_id = cfg["voice"]["voice_id"]
    rate = cfg["voice"]["rate"]

    modelo = cfg["openai"]["model"]
    temp = cfg["openai"]["temperature"]
    max_tok = cfg["openai"]["max_tokens"]

    repetidos: Counter[str] = Counter()
    buffer: Deque[str] = deque(maxlen=50)  # almacena últimas líneas para detectar repes

    with ruta_log.open("rb") as fh:
        fh.seek(0, 2)  # ir al final (modo "tail -f")
        print("[Narrador DF] Esperando eventos…")

        while True:
            nuevas = leer_nuevas_lineas(fh)
            if nuevas:
                # Filtrado inicial: quitar vacíos y control chars
                nuevas = [n for n in nuevas if n]
                if not nuevas:
                    time.sleep(0.5)
                    continue

                # Detección de repeticiones
                for linea in nuevas:
                    if linea in buffer:
                        repetidos[linea] += 1
                    buffer.append(linea)

                # Construir bloque a narrar
                bloque = nuevas.copy()
                for evento, cnt in repetidos.items():
                    if cnt >= cfg["narration"]["repeat_threshold"]:
                        bloque.append(
                            f"(⚠ Evento repetido {cnt} veces) {evento}"
                        )

                narracion = resumir_eventos(
                    bloque, modelo=modelo, temp=temp, max_tokens=max_tok
                )

                hablar(narracion, motor, voice_id, rate)
                # Mensaje corto para chat (si procede)
                long_max = cfg["stream"]["short_message_length"]
                print(
                    f"\n[Chat] {narracion[:long_max].strip()}"
                    + ("…" if len(narracion) > long_max else "")
                )

                # Reiniciar contadores tras narrar
                repetidos.clear()

            time.sleep(cfg["gamelog"]["poll_interval"])


# ---------- CLI ---------- #

def main():
    parser = argparse.ArgumentParser(description="Narrador DF – narración en vivo")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Ruta al archivo de configuración TOML",
    )
    args = parser.parse_args()
    cfg = cargar_config(args.config)
    run(cfg)


if __name__ == "__main__":
    main()
