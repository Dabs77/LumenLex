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
from docx import Document
from pypdf import PdfReader
import streamlit as st

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
    *   Mantén intactos los efectos, obligaciones, derechos, **plazos (incluyendo los de notificación)**, montos, porcentajes y cualquier requisito específico (como pólizas de seguro mencionadas en el original).
    *   **Conserva SIEMPRE todos aquellos términos legales que sean fundamentales para definir la naturaleza jurídica del contrato o de las figuras específicas que regula**, manteniendo su precisión y sin reemplazarlos por sinónimos generales que diluyan su significado. **Ejemplos de términos a conservar:** "culpa levísima", "orden de compra", "depósito gratuito", **"tenencia", "custodia", "consignación"**, "inventario físico", "factura".
    *   **Conserva y utiliza SIEMPRE los términos clave definidos en el contrato original, respetando su CAPITALIZACIÓN** (Ej: "EL PROVEEDOR", "LA INSTITUCIÓN", "PRODUCTOS", "ANEXO 1"). No uses sinónimos para estos términos definidos.
    *   No omitas información legalmente relevante, condiciones esenciales o **cláusulas enteras** presentes en el original.
    *   **No sobresimplifiques cláusulas críticas** como las de Responsabilidad, Indemnidad o Seguros. Asegúrate de que todos los aspectos centrales, incluyendo estándares de cuidado específicos (ej. "culpa levísima") y requisitos (ej. mantener pólizas), se preserven claramente.

2.  **Claridad Extrema y Lectura Fluida:**
    *   Usa lenguaje sencillo, directo y colombiano, pero SIN sacrificar la precisión legal (punto 1).
    *   **Prefiere oraciones muy cortas** (ideal ≤ 20 palabras). Una idea por oración.
    *   Usa voz activa y orden lógico (quién hace → qué hace → a quién/qué).
    *   Elimina redundancias, arcaísmos, latinismos innecesarios y dobles negaciones. **Evita específicamente frases explicativas o conversacionales** como "esto significa", "es importante notar", "punto a considerar", "para efectos de". Integra la *implicación* o el *detalle* directamente en el lenguaje contractual vinculante.
    *   Si un concepto (como el propósito del contrato) está claramente cubierto en una cláusula (ej., Objeto), evita crear una cláusula separada y repetitiva, a menos que la sección original aporte información distinta y no redundante.
    *   Usa conectores lógicos claros ("además", "por lo tanto", "sin embargo", "es decir") para guiar la lectura entre ideas.

3.  **Estructura y Diseño Accesible (para HTML/Web):**
    *   **Descompón agresivamente cláusulas originales largas que mezclan múltiples temas en cláusulas separadas y enfocadas, cada una tratando un solo tema principal.** Por ejemplo, si la cláusula original de "Objeto" también detalla la entrega, el proceso de compra post-uso y la reposición, crea cláusulas distintas para "Objeto", "Entrega", "Proceso de Compra Post-Uso", "Reposición", etc.
    *   **Asigna numeración secuencial clara** a las cláusulas resultantes (ej., Cláusula 1, Cláusula 2, Cláusula 3...). Puedes usar sub-numeración (1.1, 1.2) si es lógicamente necesario para sub-temas dentro de una cláusula principal *simplificada*, pero prefiere cláusulas separadas para temas distintos.
    *   Para cada Cláusula o sección principal (Antecedentes, etc.) del contrato *resultante* simplificado, crea **UNA entrada** en la lista `sections` del JSON.
    *   Usa **títulos claros y precisos** para cada cláusula. Si el título original es vago o impreciso (ej., "Unilateralidad" para una cláusula sobre gratuidad), usa uno que refleje mejor el contenido legal real (ej., "Gratuidad de la Tenencia").
    *   **DENTRO** de cada entrada del JSON (en el campo `simplified_text`), el texto debe estar redactado únicamente en forma de párrafos corridos, sin usar listas, bullets, viñetas, ni numeraciones. Todas las ideas deben estar hiladas en párrafos, separadas solo por puntos y comas. NO uses listas ni saltos de línea para separar puntos.
    *   Al simplificar cláusulas que involucren notificaciones o comunicaciones, asegúrate de que **cualquier plazo específico** mencionado en el original se conserve explícitamente.

4.  **Sin referencias normativas explícitas:**
    *   No cites artículos, leyes, decretos, etc. (p. ej., "artículo 1380 C. Com.").
    *   Integra la obligación o el efecto legal directamente en el texto simplificado.

5.  **Consistencia terminológica:**
    *   Una vez definas o uses un término (especialmente los conservados del original o los clave capitalizados), úsalo siempre igual en el texto simplificado.

6.  **Manejo de Placeholders:**
    *   Si encuentras placeholders como `(__)`, `_________`, `[ ]`, etc., déjalos explícitos en el texto simplificado o indica claramente que es un espacio a llenar (ej: "Plazo: [Especificar plazo en días]").

## 2. Flujo de trabajo LumenLex

1.  **Lee el contrato original completo** para entender su flujo y contenido global.
2.  **Identifica las secciones y cláusulas originales.** Presta atención a las cláusulas largas que combinan múltiples temas distintos (objeto, entrega, pago, reposición, etc.).
3.  **Planifica la nueva estructura:** Decide cómo descomponer las cláusulas complejas originales en cláusulas más simples y monotemáticas para la versión simplificada. Asigna una numeración secuencial provisional.
4.  Para cada **nueva cláusula simplificada** planificada en el paso 3 (o para secciones como Antecedentes):
    *   **Determina el número y título principal claro y preciso.** Este será el `section_title`.
    *   **Reescribe el contenido** correspondiente del original siguiendo los Principios rectores (Sección 1). **Presta especial atención a conservar los términos legales clave (punto 1.1) y descomponer en puntos claros y listas numeradas (punto 3).** Recuerda mantener plazos y requisitos específicos. Así mismo recuerda que el texto debe estar escrito en forma de parrafos, recuerda que queremos simplificar el documento pero manteniendo la estructura de parrafos. Este será el `simplified_text`.
    *   **Escribe una justificación breve** (máx. 40 palabras) explicando la estrategia de simplificación para esa Cláusula, mencionando específicamente si se descompuso de una cláusula original más grande, si se conservaron términos clave o si se renombró para mayor claridad. Este será el `justification`.
5.  Construye la lista `sections` del JSON ÚNICAMENTE con las entradas generadas en el paso 4, siguiendo el orden lógico planificado.

## 3. Salida estricta en JSON (¡NO AÑADAS TEXTO ADICIONAL FUERA DEL JSON!)

"""

diagramaprompt= """
Eres un asistente especializado en transformar contratos legales en diagramas de flujo estructurados. Al recibir el texto completo de un contrato, tu tarea es analizarlo y devolver únicamente un objeto JSON con esta forma:
Responde solo con el JSON, no añadas texto adicional.
```json
{
  "flowchart": {
    "nodes": [
      {
        "id": "start",             // identificador único, sin espacios
        "type": "start",           // uno de: "start", "process", "decision", "end"
        "label": "Firma del Contrato",  
        "metadata": {              // datos adicionales relevantes
          "date": "2025-06-01",
          "parties": ["Cliente A", "Proveedor B"]
        }
      },
      … más nodos …
    ],
    "edges": [
      {
        "from": "start",           // id del nodo origen
        "to": "approval",          // id del nodo destino
        "label": ""                // condición o texto de la arista (opcional)
      },
      … más aristas …
    ]
  }
}

"""
def extract_raw_text(file_name: str, file_bytes: bytes) -> str:
    """
    Extrae todo el texto de un archivo .docx o .pdf.
    Args:
        file_name: nombre del archivo (extensión)
        file_bytes: contenido binario
    Returns:
        Texto extraído como str
    """
    if file_name.lower().endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif file_name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError("Formato no soportado. Usa .docx o .pdf")
    if not text.strip():
        raise ValueError("No se extrajo texto válido del documento.")
    return text


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
    data = json.loads(cleaned, strict=False)
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
  <h2>{i}. {title}</h2>
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