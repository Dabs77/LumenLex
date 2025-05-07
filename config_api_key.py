import sys
import google.generativeai as genai

def setup_gemini_api(userdata, prompt_var_name='simplification_prompt'):
    """
    Configura la API Key para Gemini y verifica que exista el prompt de simplificación.
    
    Parámetros:
        userdata: objeto que provee acceso a los secretos (tiene el método .get)
        prompt_var_name: nombre de la variable global que debe estar definida
    """
    # 1. Configurar API Key de Gemini
    try:
        api_key = userdata.get('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        print("API Key de Gemini configurada.")
    except userdata.SecretNotFoundError:
        print(
            "Error: Secret 'GOOGLE_API_KEY' no encontrado. "
            "Por favor, configúralo en Google Colab (Panel izquierdo → Candado).",
            file=sys.stderr
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error configurando la API de Gemini: {e}", file=sys.stderr)
        sys.exit(1)
