import requests
import fitz
import sys

url = "https://www.indec.gob.ar/ftp/cuadros/sociedad/preguntas_frecuentes_cba_cbt.pdf"
print(f"Downloading {url}...")
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
}
try:
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    with open("cba_cbt.pdf", "wb") as f:
        f.write(r.content)
        
    doc = fitz.open("cba_cbt.pdf")
    for i, page in enumerate(doc):
        text = page.get_text()
        if "Composición de la CBA" in text or "adulto equivalente" in text.lower():
            print(f"--- PAGE {i} ---")
            print(text)
except Exception as e:
    print(f"Error: {e}")
