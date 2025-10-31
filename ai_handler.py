import ollama

class AIHandler:
    def __init__(self):
        self.client = ollama.Client()
        
    async def get_ai_response(self, prompt, model="gemma"):
        """
        Obtiene una respuesta del modelo de IA
        
        Args:
            prompt (str): El texto de entrada para el modelo
            model (str): El nombre del modelo a usar (por defecto "gemma")
            
        Returns:
            str: La respuesta generada por el modelo
        """
        try:
            response = self.client.chat(model=model, messages=[{
                'role': 'user',
                'content': prompt
            }])
            return response['message']['content']
        except Exception as e:
            print(f"Error al obtener respuesta del modelo: {e}")
            return "Lo siento, hubo un error al procesar tu solicitud con IA."

    def list_available_models(self):
        """
        Lista los modelos disponibles localmente
        
        Returns:
            list: Lista de nombres de modelos disponibles
        """
        try:
            models = self.client.list()
            return [model['name'] for model in models]
        except Exception as e:
            print(f"Error al listar modelos: {e}")
            return []