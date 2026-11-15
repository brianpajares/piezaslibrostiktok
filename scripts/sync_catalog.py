#!/usr/bin/env python3
"""Sincroniza engine/catalog.json con el catálogo de libros publicados (Sheet "Libros Publicados en Amazon").
Agrega full_title, author, amazon_kindle, amazon_paperback (URL https://www.amazon.com/dp/ASIN) y libros nuevos."""
import json, os, re, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, "engine", "catalog.json")
T = """L01|La Ruta Maestra hacia la Certificación PMP: Guía Práctica para Profesionales Exitosos|es|B0DWPB9MML|
L02|CFA: El Camino Certificado Hacia el Éxito Financiero Global|es|B0DWT17LCJ|
L03|AWS Solutions Architect Associate: Certifícate y Transforma tu Carrera en la Nube|es|B0DWT8XXXD|B0F79WNWYM
L04|MBA Rediseñado: Aprende, Lidera y Triunfa con las Estrategias que Funcionan Hoy|es|B0F5QR9FNZ|B0F7FG4QZT
L05|Arquitectura de Soluciones para Líderes Tecnológicos: Diseña, Escala y Transforma|es|B0F5NWGYNY|B0F6YJ1235
L06|Domina la Era de la Inteligencia Artificial Generativa: La Guía Definitiva para Data Scientists del Futuro|es|B0F5NV8NY5|B0F7FRTVQ7
L07|El ABC de la Innovación Minera|es|B08W8G9J9J|B08W6QDCX3
L08|Tecnología Minera en Acción: Guía Completa para Instalar, Automatizar y Sostener Soluciones con Data e Inteligencia Artificial|es|B0F59MNMN2|B0F7GCBL2Q
L09|La Transformación Digital y la Minería 4.0: La guía de todo profesional del futuro|es|B08XGDJWF6|B08XNDNPDT
L10|Liderando Start Ups del Futuro: La guía para ser un emprendedor exitoso|es|B08XHDW2P5|B08XL7ZG3H
L11|ABC of the Mining Innovation|en|B08XLMDF6S|B08XGSTPCQ
L12|All About Digital Transformation and the Mining 4.0|en|B08XLMLDQW|B08XLLDZ8Y
L13|Leading Start Ups of the Future: The guide to being a successful entrepreneur|en|B08XJV1222|B08XL7ZFCP
L14|The Master Path to PMP Certification: A Practical Guide for Successful Professionals|en|B0DWM13M4P|
L15|CFA: The Certified Path to Global Financial Success|en|B0DWQM4B7Z|
L16|Mining Technology in Action: A Complete Guide to Installing, Automating, and Sustaining Solutions with Data and Artificial Intelligence|en|B0F3VB8K2N|
L17|Master the Age of Generative Artificial Intelligence: The Ultimate Guide for Data Scientists of the Future|en|B0F5NTJ55Q|
L18|Solutions Architecture for Technology Leaders: Design, Scale, and Transform|en|B0F5QKYCJV|
L19|MBA Redesigned: Learn, Lead, and Succeed with Strategies That Work Today|en|B0F4ZMBB8W|
L20|AWS Solutions Architect Associate: Get Certified and Transform Your Career in the Cloud|en|B0DWTB2V3R|
L21|CEO Aumentado: Cómo líderes, emprendedores y profesionales pueden convertir la IA en estrategia y ventaja competitiva real|es|B0GYTJ466Y|B0GZ316BHH
L22|Chief AI Officer: El nuevo líder de la empresa inteligente|es|B0GYZYK1G7|B0GZ3BRP2K
L23|The AI Growth Operating System: How Leaders Build Agentic Workflows, Data Foundations, and New Revenue Engines|en|B0H2KJ15ZX|B0H2PWP6HX
L24|Designing Robots for Mining|en|B0H3891219|
L25|The Digital Twin Mine|en|B0H381YN82|
L26|Battery-Electric Underground Mining|en|B0H3CDGH5F|
L27|Open-Pit IoT Revolution|en|B0H3CS4K38|
L28|El Ingeniero MLOps|es|B0H482Q8VW|
L29|El Manual del Arquitecto Cloud|es|B0H47SNCWQ|
L30|El Ingeniero de IA: Construye aplicaciones GenAI de producción con LLMs, RAG y agentes|es|B0H47SQ4SK|
L31|Arquitecturas de IA para Minería|es|B0H486RBQS|
L32|From Control Room to Autonomous Mine|en|B0GXSXT8BN|
L33|The Underground Connected Mine|en|B0GX377FKH|
L34|Centro Integrado de Operaciones para Minería|es|B0H2SY42BP|
L35|The AI Digital Wealth Factory: How to Build, Automate and Monetize Digital Products with Agentic AI|en|B0H1MQ27TL|
L36|Google Cloud Engineer: Guía completa para aprobar la certificación Associate Cloud Engineer (ACE)|es|B0H4HPWHMG|
L37|Domina Azure y Certifícate Rápido: La guía total para aprobar el examen AZ-104|es|B0H4HS7VKJ|
L38|Space Mining Engineering|en|B0H4N9YHCQ|
L39|Deep-Sea Mining 2030|en|B0H4NDH523|
L40|Maintenance Data Scientist|en|B0H63XQQRJ|
L41|Computer Vision for Mine Safety|en|B0H63S13SL|
L42|VIBE CODING: The Professional System for Building, Shipping, and Scaling Software with AI Agents|en|B0H6RB9BQM|
L43|AWS Cloud Architect Blueprint|es|B0H6RBYZQY|
L44|IA para Crecimiento y Ventas Exponenciales|es|B0H6R4HYQK|
L45|Data to Dollars: Cómo convertir datos e inteligencia artificial en decisiones que generan dinero|es|B0H6RB7VXK|
L46|Loop Engineering: Diseña bucles de agentes de IA que trabajan, observan, deciden y mejoran por ti|es|B0H6RBJ8CL|
L47|AI Mineral Exploration|en|B0H72W5BBY|
L48|Arquitectura de Soluciones en la Era Cloud|es|B0H7636BT1|
L49|Generative AI for Mining|en|B0H7672M87|"""
# claves para libros que aún no estaban en el catálogo: id -> (clave, cat, tags)
NEW = {
 "L05": ("solarch-es", "neg", "#arquitecturadesoluciones #cloud #liderazgo #tecnologia #CTO"),
 "L06": ("genai-es", "ia", "#IAgenerativa #datascience #inteligenciaartificial #LLM #IA"),
 "L07": ("abcmin-es", "min", "#mineria #innovacion #mineria40 #Peru #tecnologia"),
 "L08": ("tecmin-es", "min", "#mineria #IA #automatizacion #mineria40 #Peru"),
 "L09": ("min40-es", "min", "#mineria40 #transformaciondigital #mineria #Peru #tecnologia"),
 "L11": ("abcmin-en", "min", "#mining #innovation #mining40 #miningtech #Peru"),
 "L12": ("min40-en", "min", "#mining40 #digitaltransformation #mining #miningtech #AI"),
 "L16": ("tecmin-en", "min", "#mining #AI #automation #mining40 #miningtech"),
 "L24": ("robots", "min", "#mining #robotics #automation #miningtech #engineering"),
 "L26": ("bev", "min", "#mining #batteryelectric #decarbonization #miningtech #engineering"),
 "L27": ("openpit", "min", "#mining #IoT #drones #5G #edgeAI"),
 "L31": ("iamin", "min", "#mineria #IA #mineria40 #Peru #datos"),
 "L32": ("autonomous", "min", "#mining #autonomousmining #remoteoperations #miningtech #AI"),
 "L33": ("ugconnected", "min", "#mining #IoT #private5G #undergroundmining #miningtech"),
 "L34": ("cio-min", "min", "#mineria #centrodeoperaciones #mineria40 #Peru #tecnologia"),
 "L43": ("awsblue", "cert", "#AWS #cloud #arquitecturacloud #AWSCertified #nube"),
 "L47": ("aiexplore", "min", "#mining #mineralexploration #AI #geology #miningtech"),
 "L48": ("arqera", "ia", "#arquitecturadesoluciones #cloud #nube #tecnologia #arquitectura"),
 "L49": ("genaimin", "min", "#mining #generativeAI #AI #mining40 #miningtech"),
}
SUB = {"es": "Brian Pajares · Zone Digital", "en": "Brian Pajares · Zone Digital"}

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]

def main():
    cat = json.load(open(F, encoding="utf-8"))
    books = cat["books"]; by_asin = {b["kindle"]: k for k, b in books.items()}
    added = []
    for line in T.splitlines():
        lid, full, lang, k, p = line.split("|")
        key = by_asin.get(k)
        if not key:
            if lid not in NEW:
                continue
            key, c, tags = NEW[lid]
            short = full.split(":")[0].strip()
            books[key] = {"title": short, "sub": full.split(":", 1)[1].strip() if ":" in full else SUB[lang],
                          "lang": lang, "cat": c, "kindle": k, "page": slug(short), "tags": tags}
            added.append(key)
        b = books[key]
        b.update({"id": lid, "full_title": full, "author": "Brian Pajares", "lang": lang, "kindle": k,
                  "amazon_kindle": f"https://www.amazon.com/dp/{k}",
                  "amazon_paperback": f"https://www.amazon.com/dp/{p}" if p else None})
        if p: b["paper"] = p
        else: b.pop("paper", None)
    json.dump(cat, open(F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok", len(books), "libros; nuevos:", added)

if __name__ == "__main__":
    main()
