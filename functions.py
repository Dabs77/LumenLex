"""
functions.py

Contiene la lógica para:
 - Carga de la API key desde .env
 - Extracción de texto de .docx/.pdf
 - Llamada a la API de Gemini para simplificar (modelo gemini-2.5-pro-exp-03-25)
 - Parseo de la respuesta JSON
 - Generación de HTML simplificado
 - Generación de PDF desde HTML usando WeasyPrint
"""

import os
import io
from xhtml2pdf import pisa
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import matplotlib.pyplot as plt
import anytree
from graphviz import Source
import subprocess
import re
import tempfile
import pdfplumber
from docx import Document as DocxReader 
# 1. Cargar la API Key
def load_api_key():
    load_dotenv()  # variables locales
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY no encontrada. Defínela en un archivo .env local o en Streamlit secrets"
        )
    return GOOGLE_API_KEY

GOOGLE_API_KEY = load_api_key()
# 2. Configurar la API de Gemini
genai.configure(api_key=GOOGLE_API_KEY)

simplification_prompt = """
¡Eres LumenLex! Eres el diseñador(a) legal de contratos más reconocido(a) de Colombia: combinas el rigor técnico de un abogado senior con la mirada UX de un experto en Legal Design y Lectura Fácil. Tu misión es transformar un contrato complejo en un texto 10 veces más comprensible **sin alterar su fuerza jurídica ni diluir su precisión legal**, estructurándolo y simplificándolo específicamente para una **presentación clara y accesible en formato digital (HTML/Web)**, inspirada en diseños de contratos con Legal Design.

Te basarás en los principios de Legal Design observados en contratos modernos y visualmente claros.

Tu objetivo es generar el *contenido estructurado* para las **cláusulas y secciones principales** del contrato. Ten en cuenta que la presentación HTML final incluirá, además de estas cláusulas, un **encabezado inicial con los datos clave del contrato** (Partes, NITs, fecha, etc.), que tu JSON **no** necesita replicar directamente, a menos que formen parte de los antecedentes o primeras cláusulas con texto narrativo a simplificar.

**Nota Importante sobre el Alcance:** Tu tarea principal es **simplificar y reestructurar el texto del contrato proporcionado**. El feedback recibido menciona la conveniencia de añadir cláusulas estándar que podrían faltar en el original (como Firma Electrónica, Protección de Datos, Cláusula Penal, etc.) o de reordenar drásticamente las cláusulas. **Actualmente, tu enfoque debe ser trabajar con el contenido existente.** La capacidad de sugerir o generar cláusulas completamente nuevas o de reordenar masivamente la estructura basándose en "mejores prácticas" es una funcionalidad avanzada, fuera del alcance de esta instrucción específica de simplificación del texto base.

## INSTRUCCIÓN ADICIONAL IMPORTANTE:
Nunca uses el símbolo $ en el texto simplificado. Siempre escribe la palabra "pesos" o "dólares" según corresponda.

## 1. Principios rectores para Legal Design y Lectura Fácil (¡Rigor Técnico y Claridad!)

1.  **Fidelidad jurídica absoluta y Precisión Técnica:**
    * Mantén intactos los efectos, obligaciones, derechos, **plazos (incluyendo los de notificación)**, montos, porcentajes y cualquier requisito específico (como pólizas de seguro mencionadas en el original).
    * **Conserva SIEMPRE todos aquellos términos legales que sean fundamentales para definir la naturaleza jurídica del contrato o de las figuras específicas que regula**, manteniendo su precisión y sin reemplazarlos por sinónimos generales que diluyan su significado. **Ejemplos de términos a conservar:** "culpa levísima", "orden de compra", "depósito gratuito", **"tenencia", "custodia", "consignación"**, "inventario físico", "factura".
    * **Conserva y utiliza SIEMPRE los términos clave definidos en el contrato original, respetando su CAPITALIZACIÓN** (Ej: "EL PROVEEDOR", "LA INSTITUCIÓN", "PRODUCTOS", "ANEXO 1"). No uses sinónimos para estos términos definidos.
    * No omitas información legalmente relevante, condiciones esenciales o **cláusulas enteras** presentes en el original.
    * **No sobresimplifiques cláusulas críticas** como las de Responsabilidad, Indemnidad o Seguros. Asegúrate de que todos los aspectos centrales, incluyendo estándares de cuidado específicos (ej. "culpa levísima") y requisitos (ej. mantener pólizas), se preserven claramente.
    * **Preserva la intención y el matiz exacto de frases legales específicas** (ej. "sin perjuicio de que", "en defecto de", "a su entera discreción", "a pesar de esto"). No alteres su significado al simplificar.

2.  **Claridad Extrema y Lectura Fluida:**
    * Usa lenguaje sencillo, directo y colombiano, pero SIN sacrificar la precisión legal (punto 1).
    * **Prefiere oraciones muy cortas** (ideal ≤ 20 palabras). Una idea por oración.
    * Usa voz activa y orden lógico (quién hace → qué hace → a quién/qué).
    * Elimina redundancias, arcaísmos, latinismos innecesarios y dobles negaciones. **Evita específicamente frases explicativas o conversacionales** como "esto significa", "es importante notar", "punto a considerar", "para efectos de". Integra la *implicación* o el *detalle* directamente en el lenguaje contractual vinculante.
    * Si un concepto (como el propósito del contrato) está claramente cubierto en una cláusula (ej., Objeto), evita crear una cláusula separada y repetitiva, a menos que la sección original aporte información distinta y no redundante.
    * Usa conectores lógicos claros ("además", "por lo tanto", "sin embargo", "es decir") para guiar la lectura entre ideas.

3.  **Estructura y Diseño Accesible (para HTML/Web):**
    * **Descompón cláusulas originales largas que claramente mezclan múltiples temas principales y funcionalmente distintos** en cláusulas separadas y enfocadas. Por ejemplo, si una cláusula original de "Objeto" también detalla extensamente la entrega, el proceso de compra y la reposición, considera crear cláusulas distintas para "Objeto", "Entrega", "Proceso de Compra", "Reposición", etc. **Sin embargo, evita fragmentar excesivamente cláusulas que, aunque puedan tener varios puntos, tratan un tema unificado y coherente** (ej. una única cláusula de "Obligaciones de LA PARTE CONTRATISTA" que enumera varios deberes). En estos casos, la simplificación debe ocurrir *dentro* de los puntos enumerados si el original ya los tenía, o agrupando temáticamente el contenido, manteniendo la cláusula unificada bajo su título original o uno más preciso.
    * **MODIFICADO ADICIONALMENTE:** **Numeración y Títulos de Secciones/Cláusulas:** Asigna una numeración secuencial arábiga a cada sección principal o cláusula resultante del contrato simplificado (empezando desde 1 para la primera sección, sea "Consideraciones", "Antecedentes" o la primera cláusula numerable). El `section_title` en el JSON debe reflejar esta numeración seguida de un punto, un espacio y el título descriptivo de la sección o cláusula (ej: "1. Consideraciones", "2. Objeto del Contrato", "15. Obligaciones de LA PARTE CONTRATISTA"). Utiliza títulos claros y precisos que reflejen fielmente el contenido legal real de la cláusula. Si el título original es vago o impreciso (ej., "Unilateralidad" para una cláusula sobre gratuidad), mejóralo (ej., "8. Gratuidad de la Tenencia").
    * Para cada Cláusula o sección principal (Antecedentes, Consideraciones, etc.) del contrato *resultante* simplificado, crea **UNA entrada** en la lista `sections` del JSON.
    * **DENTRO** de cada entrada del JSON (en el campo `simplified_text`), estructura el contenido para máxima legibilidad digital:
        * **Conserva el formato de párrafo del texto original como la forma de presentación por defecto.** El texto simplificado debe ser continuo, usando solo puntos y comas para separar ideas dentro de los párrafos. **No uses saltos de línea (`\\n`) para separar oraciones dentro de un mismo párrafo o entre párrafos de texto corrido.**
        * **Utiliza una estructura de lista (con ítems separados por `\\n` y marcadores) ÚNICAMENTE en las siguientes situaciones:**
            * **Si el contenido original ya está presentado explícitamente como una lista** (ej. con literales `a), b), c)`; numeración `1., 2., 3.`; o sub-puntos `X.1, X.2`). En este caso, mantén la estructura de lista usando los formatos especificados a continuación.
            * **Si un párrafo original contiene una enumeración clara de múltiples ítems, obligaciones, condiciones, causales o pasos distintos, y presentarlos como una lista mejora significativamente la claridad y la legibilidad en el formato digital.** Esta transformación de párrafo a lista debe ser usada con criterio y de forma excepcional, solo cuando la estructura de párrafo original resulte genuinamente confusa o muy densa para presentar dicha enumeración de forma comprensible.
        * **Cuando se utilice una estructura de lista,** cada ítem debe ser una frase u oración concisa. Para la salida JSON, representa esta lista concatenando los ítems, usando uno de los siguientes formatos de marcadores y separando cada ítem completo (marcador y texto) con un salto de línea `\\n`:
            * **Formato Numérico:** Utiliza una numeración secuencial. Si los ítems son subpuntos directos de una cláusula principal cuyo título es, por ejemplo, "2. Obligaciones", numéralos como `2.1 Texto del ítem.`, `2.2 Texto del ítem.`, etc. Si es una lista general dentro de una cláusula y no se corresponde directamente con el número de la cláusula principal, puedes usar `1. Texto del ítem.`, `2. Texto del ítem.`, etc.
            * **Formato Alfabético:** Utiliza literales secuenciales como `a) Texto del ítem.`, `b) Texto del ítem.`, `c) Texto del ítem.`, etc.
        * **Preferencia de Formato para Listas:** Si el texto original ya utiliza un formato de lista específico (ej. `a), b), c)` o `1., 2., 3.` o `II.1, II.2`), utiliza preferentemente ese mismo estilo de formato en la versión simplificada, adaptándolo para la claridad y consistencia con los formatos aquí descritos si es necesario. Si estás transformando una enumeración de un párrafo a una lista (bajo el criterio de excepcionalidad mencionado), puedes elegir el formato (numérico o alfabético) que consideres más claro.
        * Ejemplo de salida JSON para texto en párrafo corrido: `"Este es un párrafo. Describe una idea completa. Este es otro pensamiento dentro del mismo párrafo."`
        * Ejemplo de salida JSON para formato de lista alfabético: `a) Primer ítem.\\nb) Segundo ítem.\\nc) Tercer ítem.`
        * Ejemplo de salida JSON para formato de lista numérico (subpuntos de "Cláusula 2"): `2.1 Primer ítem.\\n2.2 Segundo ítem.\\n2.3 Tercer ítem.`
        * **Mantén la integridad de la información de cada punto original de la lista al simplificarlo.**
        * **Evita el uso de sub-numeración más allá de un nivel (ej. `X.Y`) directamente en el `simplified_text` (es decir, no uses `X.Y.Z` o `a.i.1`).**
    * Al simplificar cláusulas que involucren notificaciones o comunicaciones, asegúrate de que **cualquier plazo específico** mencionado en el original se conserve explícitamente.

4.  **Sin referencias normativas explícitas:**
    * No cites artículos, leyes, decretos, etc. (p. ej., "artículo 1380 C. Com.").
    * Integra la obligación o el efecto legal directamente en el texto simplificado.

5.  **Consistencia terminológica:**
    * Una vez definas o uses un término (especialmente los conservados del original o los clave capitalizados), úsalo siempre igual en el texto simplificado.

6.  **Manejo de Placeholders:**
    * Si encuentras placeholders como `(__)`, `_________`, `[ ]`, etc., déjalos explícitos en el texto simplificado o indica claramente que es un espacio a llenar (ej: "Plazo: [Especificar plazo en días]").

## 2. Flujo de trabajo LumenLex

1.  **Lee el contrato original completo** para entender su flujo y contenido global.
2.  **Identifica las secciones y cláusulas originales.** Presta atención a si el texto está en párrafos corridos o si ya utiliza estructuras de lista. Planifica la numeración secuencial de las secciones/cláusulas principales resultantes.
3.  **Planifica la nueva estructura:** Decide cómo descomponer las cláusulas complejas originales (que mezclan temas funcionalmente distintos) en cláusulas más simples y monotemáticas. Determina si el contenido de una cláusula se mantendrá como párrafo corrido o si, excepcionalmente, una enumeración en un párrafo se transformará a formato de lista para mayor claridad, o si se mantendrá un formato de lista original.
4.  Para cada **nueva cláusula simplificada** planificada en el paso 3 (o para secciones como Antecedentes/Consideraciones):
    * **MODIFICADO ADICIONALMENTE:** **Determina el número secuencial de la cláusula/sección y su título descriptivo.** Con base en la numeración planificada (ver punto 1.3), el `section_title` debe ser formateado como `"Número. Título descriptivo"` (ej., `"1. Consideraciones"`, `"2. Objeto del Contrato"`).
    * **Reescribe el contenido** correspondiente del original siguiendo los Principios rectores (Sección 1). **Prioriza el formato de párrafo corrido.** Usa estructuras de lista (con formatos `X.1`, `1.`, o `a)`) y saltos de línea `\\n` únicamente según las condiciones restrictivas del punto 1.3. Recuerda mantener plazos y requisitos específicos. Si la cláusula original ya estaba estructurada como una lista, mantén esa estructura, aplicando el formato de marcador elegido y simplificando cada ítem. Este será el `simplified_text`.
    * **Escribe una justificación breve** (máx. 40 palabras) explicando la estrategia de simplificación para esa Cláusula. Menciona si se mantuvo el formato de párrafo, si se conservó o aplicó un formato de lista específico (y cuál y por qué, especialmente si se transformó un párrafo a lista). Este será el `justification`.
5.  Construye la lista `sections` del JSON ÚNICAMENTE con las entradas generadas en el paso 4, siguiendo el orden lógico planificado.

## 3. Salida estricta en JSON (¡NO AÑADAS TEXTO ADICIONAL FUERA DEL JSON!)
```json
{
  "type": "object",
  "properties": {
    "sections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "section_title":      { "type": "string" },
          "simplified_text":  { "type": "string" },
          "justification":      { "type": "string" }
        },
        "required": ["section_title","simplified_text","justification"]
      }
    }
  },
  "required": ["sections"]
}
"""

diagramaprompt= """
Analiza el anterior texto y determina qué tipo de visualización necesita.

IMPORTANTE: Si generas un grafo de relación, asegúrate de que los valores de x e y de los nodos estén suficientemente separados (por ejemplo, usa valores entre -100 y 100, pero evita que varios nodos tengan valores muy cercanos). Además, si hay relaciones de dirección, indícalo en la estructura (usa conexiones dirigidas).

Genera una respuesta en formato JSON siguiendo una de estas estructuras según el tipo de visualización, es importante que solo devuelvas el JSON y nada más de texto:

1. Para LÍNEA DE TIEMPO:
{
  "category": "tiempo",
  "parameters": {
    "isTimeline": true,
    "title": "Título descriptivo",
    "events": [
      {
        "date": "Fecha específica",
        "title": "Título del evento",
        "description": "Descripción detallada",
        "icon": "📄"  // Emoji relevante
      }
    ]
  }
}

2. Para COMPARACIÓN:
{
  "category": "comparación",
  "parameters": {
    "title": "Título descriptivo",
    "items": [
      {
        "name": "Nombre del elemento",
        "value": 100,
        "icon": "💼",  // Emoji relevante
        "color": "bg-blue-500"  // Opcional
      }
    ]
  }
}

3. Para JERARQUÍA:
{
  "category": "jerarquía",
  "parameters": {
    "title": "Título descriptivo",
    "root": {
      "name": "Nodo principal",
      "size": 100,
      "icon": "🏢",  // Emoji relevante
      "children": [
        {
          "name": "Subnodo",
          "size": 50,
          "icon": "👥"
        }
      ]
    }
  }
}

4. Para RELACIÓN:
{
  "category": "relación",
  "parameters": {
    "title": "Título descriptivo",
    "nodes": [
      {
        "name": "Nodo 1",
        "x": 0,    // Valores entre -100 y 100 para mejor distribución
        "y": 0,    // Valores entre -100 y 100 para mejor distribución
        "icon": "💡",
        "color": "bg-blue-500",  // Color opcional
        "connections": ["Nodo 2"]
      },
      {
        "name": "Nodo 2",
        "x": 50,   // Ejemplo de posición a la derecha
        "y": -50,  // Ejemplo de posición arriba
        "icon": "🔧",
        "connections": ["Nodo 3"]
      },
      {
        "name": "Nodo 3",
        "x": -50,  // Ejemplo de posición a la izquierda
        "y": 50,   // Ejemplo de posición abajo
        "icon": "📊",
        "connections": ["Nodo 1"]
      }
    ]
  }
}

5. Para GEOGRAFÍA:
{
  "category": "geografía",
  "parameters": {
    "title": "Título descriptivo",
    "gridLines": 10,  // Opcional: número de líneas en la cuadrícula
    "areas": [
      {
        "name": "Área 1",
        "startX": 0,   // Porcentaje (0-100)
        "startY": 0,   // Porcentaje (0-100)
        "endX": 50,    // Porcentaje (0-100)
        "endY": 50,    // Porcentaje (0-100)
        "color": "#E5E7EB"  // Color opcional
      }
    ],
    "nodes": [
      {
        "name": "Ubicación 1",
        "x": 25,      // Porcentaje (0-100)
        "y": 25,      // Porcentaje (0-100)
        "icon": "📍",  // Emoji relevante
        "area": "Área 1",
        "description": "Descripción de la ubicación"
      }
    ]
  }
}
"""
def _convert_docx_to_pdf_libreoffice(path_docx: str, output_dir: str):
    """
    Convierte un .docx a .pdf usando LibreOffice en modo headless.
    Crea un PDF con el mismo nombre en output_dir.
    Requiere tener 'soffice' (LibreOffice) en el PATH.
    """
    cmd = [
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        path_docx
    ]
    proceso = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proceso.returncode != 0:
        raise RuntimeError(f"Error al convertir .docx a PDF con LibreOffice:\n{proceso.stderr.decode(errors='ignore')}")

def extract_raw_text(file_name: str, file_bytes: bytes) -> str:
    """
    Extrae texto de un .docx o .pdf.
    
    - Si es .docx, primero intenta convertirlo a PDF con LibreOffice y después extraer texto
      con pdfplumber (para preservar viñetas/listas).
    - Si la conversión con LibreOffice falla (p. ej. en Linux sin soffice instalado),
      cae en un fallback que utiliza python-docx para extraer el texto directamente
      del .docx (sin pasar por PDF).
    - Si es .pdf, utiliza pdfplumber para extraer texto directamente.
    """
    lower = file_name.lower()

    # ---------- CASO A: LLEGA UN .DOCX ------------ 
    if lower.endswith(".docx"):
        # 1) Guardar el .docx en un temporal
        tmp_docx = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp_docx.write(file_bytes)
        tmp_docx.flush()
        tmp_docx.close()

        tmp_pdf_path = tmp_docx.name.replace(".docx", ".pdf")
        texto = ""

        # 2) Intentar convertir con LibreOffice a PDF para luego usar pdfplumber
        try:
            _convert_docx_to_pdf_libreoffice(tmp_docx.name, os.path.dirname(tmp_pdf_path))
            # Si esta línea no arroja excepción, ahora debería existir tmp_pdf_path
            # Extraemos texto de ese PDF con pdfplumber:
            texto_paginas = []
            with pdfplumber.open(tmp_pdf_path) as pdf:
                for pagina in pdf.pages:
                    texto_paginas.append(pagina.extract_text() or "")
            texto = "\n".join(texto_paginas).strip()

            # Limpiar archivos temporales
            os.unlink(tmp_docx.name)
            if os.path.exists(tmp_pdf_path):
                os.unlink(tmp_pdf_path)

        except Exception:
            # --- FALLBACK: LibreOffice NO está instalado o la conversión falló ---
            # Intentamos extraer directamente con python-docx:
            try:
                doc = DocxReader(tmp_docx.name)
                # Concatenamos todos los párrafos no vacíos
                partes = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
                texto = "\n".join(partes).strip()
            except Exception as e_docx:
                # Si tampoco está python-docx o hay algún error leyendo el .docx, avisamos:
                # Limpiamos antes el temporal y lanzamos un error claro.
                os.unlink(tmp_docx.name)
                raise RuntimeError(
                    "No se pudo convertir el .docx a PDF (falta LibreOffice) "
                    "ni extraer texto con python-docx. "
                    "Instala LibreOffice o python-docx.\n"
                    f"Detalles internos: {e_docx}"
                )
            finally:
                # Borrar el archivo .docx temporal
                if os.path.exists(tmp_docx.name):
                    os.unlink(tmp_docx.name)

            # Ya tenemos 'texto' con el contenido extraído y podemos retornarlo:
            if not texto:
                raise ValueError("No se extrajo texto válido del .docx usando python-docx.")
            return texto

    # ---------- CASO B: LLEGA UN .PDF ------------ 
    elif lower.endswith(".pdf"):
        # 1) Guardar el PDF en un temporal
        tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_pdf.write(file_bytes)
        tmp_pdf.flush()
        tmp_pdf.close()

        texto_paginas = []
        try:
            with pdfplumber.open(tmp_pdf.name) as pdf:
                for pagina in pdf.pages:
                    texto_paginas.append(pagina.extract_text() or "")
            texto = "\n".join(texto_paginas).strip()
        finally:
            os.unlink(tmp_pdf.name)

    else:
        raise ValueError("Formato no soportado. Usa .docx o .pdf")

    if not texto:
        raise ValueError("No se extrajo texto válido del documento.")
    return texto


# --------------------------------------------------------------------
# Necesitas definir esta función para invocar LibreOffice en caso de que
# quieras mantener esa ruta (solo aplica si tu máquina local tiene soffice):
# --------------------------------------------------------------------
def _convert_docx_to_pdf_libreoffice(docx_path: str, output_dir: str):
    """
    Convierte un .docx a .pdf usando LibreOffice en modo headless.
    Esto debería funcionar en Linux, macOS y Windows si LibreOffice está en el PATH.

    Lanza FileNotFoundError si 'soffice' no existe en el PATH.
    Lanza CalledProcessError si la conversión falla.
    """
    import subprocess

    # El comando 'soffice' es el binario de LibreOffice (Linux/Mac/Windows).
    # --headless para que no abra GUI; --convert-to pdf para conversión.
    cmd = [
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        docx_path
    ]
    # Esto puede lanzar FileNotFoundError (si no está soffice) o CalledProcessError.
    subprocess.run(cmd, check=True)

def simplify_contract(raw_text: str) -> dict:
    """
    Envía el texto a Gemini (modelo gemini-2.5-pro-exp-03-25)
    y devuelve el JSON con secciones simplificadas.
    Args:
        raw_text: contrato original en texto
    Returns:
        Dict con clave 'sections'
    """
    prompt = (
        simplification_prompt +
        "\n\nRECUERDA: El texto simplificado de cada sección debe estar redactado ÚNICAMENTE en forma de párrafos corridos, sin bullets, sin listas, sin viñetas, sin numeraciones, sin saltos de línea innecesarios. Todas las ideas deben estar hiladas en párrafos, separadas solo por puntos y comas. NO uses listas ni saltos de línea para separar puntos.\n" +
        "\n\n## Contrato Original para Simplificar:\n\n"
        + raw_text
    )
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    response = model.generate_content(prompt)
    if not response.candidates:
        raise RuntimeError("La API no devolvió candidatos.")
    candidate = response.candidates[0]
    content = (
        candidate.content.parts[0].text
        if getattr(candidate, 'content', None) and candidate.content.parts
        else response.text
    )
    cleaned = content.strip().lstrip('```json').rstrip('```').strip()
    # Intenta extraer solo el bloque JSON (entre { y } o [ y ])
    match = re.search(r'({[\s\S]*})', cleaned) or re.search(r'(\[[\s\S]*\])', cleaned)
    if match:
        cleaned = match.group(1)
    try:
        data = json.loads(cleaned, strict=False)
    except Exception as e:
        raise ValueError(f"Error al parsear JSON de Gemini: {e}\nRespuesta cruda:\n{cleaned}")
    if 'sections' not in data or not isinstance(data['sections'], list):
        raise ValueError("Respuesta JSON inválida: falta 'sections'.")
    return data


def generate_html(data: dict, source_filename: str) -> str:
    """
    Construye y devuelve un string HTML con secciones simplificadas.
    Args:
        data: dict con 'sections'
        source_filename: nombre del archivo original
    Returns:
        HTML listo para renderizar
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Contrato Simplificado - {source_filename}</title>
  <style>
    body {{ font-family: sans-serif; line-height:1.5; padding:1cm; }}
    h1 {{ text-align:center; color:#1a5276; }}
    h2 {{ color:#2980b9; margin-top:1.5em; }}
    .justification {{ font-style:italic; font-size:0.9em; background:#eef6fb; padding:0.5em; }}
    p {{ margin:0.4em 0; }}
  </style>
</head>
<body>
  <h1>LumenLex Contrato Simplificado</h1>
  <p><strong>Archivo fuente:</strong> {source_filename}</p>
  <p><strong>Generado el:</strong> {date_str}</p>
  <hr/>
"""
    for i, sec in enumerate(data['sections'], start=1):
        title = sec.get('section_title', f'Cláusula {i}')
        raw = sec.get('simplified_text', '')
        paras = ''.join(f"<p>{line}</p>" for line in raw.split("\n") if line.strip())
        just = sec.get('justification', '')
        html += f"""
  <h2>{title}</h2>
  {paras}
  <div class=\"justification\"><strong>Justificación:</strong> {just}</div>
  <hr/>
"""
    html += "</body>\n</html>"
    return html


def generate_pdf_from_html(html_content: str) -> bytes:
    """
    Genera un PDF desde HTML usando xhtml2pdf (pisa).
    Inyecta CSS específico para PDF sin afectar la vista HTML en navegador.
    """
    # CSS adicional solo para PDF: reduce márgenes y espacios
    override_css = """
    <style>
      p { margin:1px 0 !important; padding:0 !important; }
      h1 { margin:2px 0 !important; }
      h2 { margin:2px 0 !important; }
      hr { margin:2px 0 !important; }
    </style>
    """
    # Insertar override_css justo antes de </head>
    if '</head>' in html_content:
        html_pdf = html_content.replace('</head>', f"{override_css}</head>")
    else:
        # si no encuentra head, anteponer al inicio
        html_pdf = override_css + html_content

    result = io.BytesIO()
    # Pisa renderiza el HTML modificado
    status = pisa.CreatePDF(src=html_pdf, dest=result)
    if status.err:
        raise RuntimeError("Error generando PDF con xhtml2pdf")
    return result.getvalue()


def refine_section_with_instruction(section: dict, instruction: str) -> dict:
    """
    Recibe una sección JSON (section_title, simplified_text, justification)
    y una instrucción para refinar la sección.

    Retorna la sección refinada con el mismo formato JSON esperado.

    NOTA: Usa el modelo Gemini, prompt adaptado para recibir solo la sección y la instrucción.
    """
    prompt = f"""
Eres LumenLex. Ya simplificaste la siguiente cláusula de un contrato:

Título: {section['section_title']}

Texto simplificado actual:
\"\"\"
{section['simplified_text']}
\"\"\"

Justificación actual:
\"\"\"
{section.get('justification', '')}
\"\"\"

Por favor, refina este texto aplicando la siguiente instrucción:
\"\"\"
{instruction}
\"\"\"

Devuelve solo el JSON con los campos:
- section_title: el título puede ser ajustado o igual
- simplified_text: el texto refinado
- justification: una nueva justificación breve explicando el cambio (máximo 40 palabras)

Sigue exactamente este formato JSON, sin añadir texto extra fuera del JSON:
{{
  "section_title": "...",
  "simplified_text": "...",
  "justification": "..."
}}
"""
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    response = model.generate_content(prompt)
    if not response.candidates:
        raise RuntimeError("La API no devolvió candidatos.")

    candidate = response.candidates[0]
    content = (
        candidate.content.parts[0].text
        if getattr(candidate, 'content', None) and candidate.content.parts
        else response.text
    )
    cleaned = content.strip().lstrip('```json').rstrip('```').strip()
    refined_section = json.loads(cleaned, strict=False)

    # Validar claves mínimas
    if not all(k in refined_section for k in ("section_title", "simplified_text", "justification")):
        raise ValueError("Respuesta JSON inválida de refinamiento")

    return refined_section


def refine_all_sections_with_instruction(data: dict, instruction: str) -> dict:
    """
    Recibe el dict completo del contrato simplificado (con 'sections') y una instrucción global.
    Retorna un nuevo dict con todas las secciones refinadas usando la instrucción.
    """
    refined_sections = []
    for section in data.get('sections', []):
        refined = refine_section_with_instruction(section, instruction)
        refined_sections.append(refined)
    return {"sections": refined_sections}

def json_to_flowchart(data):
    dot = Digraph(comment='Diagrama de Flujo')
    dot.attr(rankdir='LR')
    shape_map = {'start':'circle','end':'doublecircle','process':'box','decision':'diamond'}
    
    for node in data['flowchart']['nodes']:
        node_id = node['id']
        dot.node(node_id, label=node['label'], shape=shape_map.get(node.get('type','process'),'box'))
    
    for edge in data['flowchart']['edges']:
        frm, to = edge['from'], edge['to']
        if edge.get('label'):
            dot.edge(frm, to, label=edge['label'])
        else:
            dot.edge(frm, to)
    
    return dot

def contract_to_visualization_json(raw_text: str) -> dict:
    """
    Envía el texto del contrato a Gemini usando diagramaprompt y devuelve el JSON de visualización.
    Args:
        raw_text: contrato original en texto
    Returns:
        Dict con la estructura de visualización
    """
    prompt = (
        "\n\nTEXTO DEL CONTRATO PARA VISUALIZACIÓN:\n\n" + raw_text+diagramaprompt 
        
    )
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    response = model.generate_content(prompt)
    if not response.candidates:
        raise RuntimeError("La API no devolvió candidatos.")
    candidate = response.candidates[0]
    content = (
        candidate.content.parts[0].text
        if getattr(candidate, 'content', None) and candidate.content.parts
        else response.text
    )
    cleaned = content.strip().lstrip('```json').rstrip('```').strip()
    data = json.loads(cleaned, strict=False)
    if 'category' not in data or 'parameters' not in data:
        raise ValueError("Respuesta JSON inválida: falta 'category' o 'parameters'.")
    return data

# Funciones de visualización para cada tipo

def render_timeline(parameters):
    # parameters: {isTimeline, title, events: [{date, title, description, icon}]}
    import pandas as pd
    df = pd.DataFrame(parameters['events'])
    fig = go.Figure()
    for i, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['date']],
            y=[1],
            mode='markers+text',
            marker=dict(size=20),
            text=[f"{row['icon']} {row['title']}<br>{row['description']}"],
            textposition="top center"
        ))
    fig.update_layout(title=parameters.get('title', 'Línea de Tiempo'), showlegend=False, yaxis=dict(visible=False))
    return fig

def render_comparison(parameters):
    # parameters: {title, items: [{name, value, icon, color}]}
    names = [f"{item.get('icon','')} {item['name']}" for item in parameters['items']]
    values = [item['value'] for item in parameters['items']]
    colors = [item.get('color', 'blue') for item in parameters['items']]
    fig = go.Figure([go.Bar(x=names, y=values, marker_color=colors)])
    fig.update_layout(title=parameters.get('title', 'Comparación'))
    return fig

def render_hierarchy(parameters):
    # parameters: {title, root: {...}}

    def build_tree(node):
        children = [build_tree(child) for child in node.get('children',[])]
        return anytree.Node(f"{node.get('icon','')} {node['name']}", size=node.get('size',1), children=children)
    root = build_tree(parameters['root'])
    dot = anytree.exporter.DotExporter(root)
    src = Source(''.join(dot))
    return src

def _map_bg_color_to_hex(bg_color):
    # Mapea clases tailwind como 'bg-blue-500' a colores hex básicos
    mapping = {
        'bg-blue-500': '#3B82F6',
        'bg-red-500': '#EF4444',
        'bg-green-500': '#22C55E',
        'bg-purple-500': '#A21CAF',
        'bg-gray-500': '#6B7280',
        'bg-yellow-500': '#EAB308',
        'bg-pink-500': '#EC4899',
        'bg-orange-500': '#F97316',
        'bg-teal-500': '#14B8A6',
        'bg-indigo-500': '#6366F1',
    }
    if not bg_color:
        return '#3B82F6'
    if bg_color.startswith('#') and len(bg_color) == 7:
        return bg_color
    return mapping.get(bg_color, '#3B82F6')

def render_relation(parameters):
    # parameters: {title, nodes: [{name, x, y, icon, color, connections}]}
    G = nx.DiGraph()
    pos = {}
    node_colors = []
    for node in parameters['nodes']:
        G.add_node(node['name'], icon=node.get('icon',''), color=node.get('color','blue'))
        pos[node['name']] = (node['x']*3, node['y']*3)
        node_colors.append(_map_bg_color_to_hex(node.get('color','bg-blue-500')))
    for node in parameters['nodes']:
        for conn in node.get('connections', []):
            G.add_edge(node['name'], conn)
    fig, ax = plt.subplots(figsize=(12, 8))
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1200, ax=ax)
    nx.draw_networkx_edges(G, pos, arrowstyle='-|>', arrowsize=30, edge_color='black', ax=ax, connectionstyle='arc3,rad=0.1')
    # Ajusta el tamaño de fuente y usa bbox para que los nombres no se salgan ni se superpongan
    nx.draw_networkx_labels(
        G, pos, font_size=10, font_weight='bold', ax=ax,
        verticalalignment='bottom',
        bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.3', alpha=0.8)
    )
    ax.set_axis_off()
    # Ajusta los límites para dejar margen extra
    x_vals, y_vals = zip(*pos.values())
    ax.set_xlim(min(x_vals)-20, max(x_vals)+20)
    ax.set_ylim(min(y_vals)-20, max(y_vals)+20)
    plt.tight_layout()
    return fig

def render_geography(parameters):
    # parameters: {title, gridLines, areas, nodes}
    fig = go.Figure()
    for area in parameters.get('areas', []):
        fig.add_shape(type="rect",
            x0=area['startX'], y0=area['startY'], x1=area['endX'], y1=area['endY'],
            line=dict(color=area.get('color','#E5E7EB')),
            fillcolor=area.get('color','#E5E7EB'), opacity=0.3)
    for node in parameters.get('nodes', []):
        fig.add_trace(go.Scatter(
            x=[node['x']], y=[node['y']],
            mode='markers+text',
            marker=dict(size=15),
            text=[f"{node.get('icon','')} {node['name']}<br>{node.get('description','')}"],
            textposition="top center"
        ))
    fig.update_layout(title=parameters.get('title', 'Geografía'), showlegend=False)
    return fig

def restructure_sections_with_instruction(data: dict, instruction: str) -> dict:
    """
    Permite eliminar o combinar secciones del contrato simplificado según una instrucción global.
    Envía el JSON completo y la instrucción a Gemini y espera un nuevo JSON con la estructura modificada.
    """
    prompt = f"""
    Eres LumenLex, experto en simplificación y edición de contratos. 
    A continuación tienes el contrato simplificado en formato JSON (solo el array de 'sections').
    Aplica la siguiente instrucción global, que puede implicar eliminar secciones, fusionar varias en una sola, o ambas cosas:

    INSTRUCCIÓN:
    """
    {instruction}
    """

    IMPORTANTE:
    - Si debes combinar secciones, crea una nueva sección con un título claro y unifica los textos y justificaciones.
    - Si debes eliminar secciones, simplemente omítelas del array final.
    - Devuelve SOLO el array de 'sections' resultante, sin ningún texto adicional.

    CONTRATO SIMPLIFICADO (array de secciones):
    {json.dumps(data['sections'], ensure_ascii=False, indent=2)}

    Devuelve el array de secciones resultante en formato JSON.
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    response = model.generate_content(prompt)
    if not response.candidates:
        raise RuntimeError("La API no devolvió candidatos.")
    candidate = response.candidates[0]
    content = (
        candidate.content.parts[0].text
        if getattr(candidate, 'content', None) and candidate.content.parts
        else response.text
    )
    cleaned = content.strip().lstrip('```json').rstrip('```').strip()
    sections = json.loads(cleaned, strict=False)
    if not isinstance(sections, list):
        raise ValueError("La respuesta no es un array de secciones.")
    return {"sections": sections}

def general_restructure_contract(text: str, instruction: str, response: dict) -> dict:
    """
    Reestructura el contrato simplificado según la instrucción dada.
    Solo revisa el texto original si la instrucción requiere buscar o agregar algo que no está en el JSON.
    Devuelve un nuevo JSON con el mismo formato que la primera vez que se simplificó (clave 'sections').
    """
    print("menas")
    print(instruction)
    prompt = f"""
    Eres LumenLex, experto en simplificación y edición de contratos.
    Recibes el siguiente json: 
    {response}
    
    A ese json debes aplicar la siguiente instrucción:
    {instruction}
    Devuelve SOLO el nuevo JSON MODIFICADO, sin ningún texto adicional, de la siguiente forma:
    """ + """
    ## 3. Salida estricta en JSON (¡NO AÑADAS TEXTO ADICIONAL FUERA DEL JSON!)
json
{
  "type": "object",
  "properties": {
    "sections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "section_title":      { "type": "string" },
          "simplified_text":   { "type": "string" },
          "justification":      { "type": "string" }
        },
        "required": ["section_title","simplified_text","justification"]
      }
    }
  },
  "required": ["sections"]
}
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    print(prompt)
    response_llm = model.generate_content(prompt)
    
    if not response_llm.candidates:
        raise RuntimeError("La API no devolvió candidatos.")
    candidate = response_llm.candidates[0]
    content = (
        candidate.content.parts[0].text
        if getattr(candidate, 'content', None) and candidate.content.parts
        else response_llm.text
    )
    print(content)
    cleaned = content.strip().lstrip('```json').rstrip('```').strip()
    # Intenta extraer solo el bloque JSON (entre { y } o [ y ])
    match = re.search(r'({[\s\S]*})', cleaned) or re.search(r'(\[[\s\S]*\])', cleaned)
    if match:
        cleaned = match.group(1)
    try:
        data = json.loads(cleaned, strict=False)
    except Exception as e:
        raise ValueError(f"Error al parsear JSON de Gemini: {e}\nRespuesta cruda:\n{cleaned}")
    if 'sections' not in data or not isinstance(data['sections'], list):
        raise ValueError("Respuesta JSON inválida: falta 'sections'.")
    return data