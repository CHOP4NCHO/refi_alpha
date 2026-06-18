import requests
from langchain_ollama import ChatOllama
from langchain.chat_models import BaseChatModel, init_chat_model
from langchain.embeddings import init_embeddings

class ModelProvider:
    def __init__(self, ip: str, local_model: str, fallback_model: str):
        """
        Inicializa el proveedor de modelos.
        
        :param ip: La dirección IP donde corre el servidor Ollama (ej: 'localhost' o '192.168.1.10')
        :param model: El nombre del modelo a utilizar (ej: 'qwen3.5', 'llama3')
        """
        self.ip = ip
        self.local_model = local_model
        self.fallback_model = fallback_model
        # Intentamos conectar al puerto por defecto de Ollama (11434) para validar disponibilidad
        self.is_ollama_reachable = self._check_connection(self.ip)

    def _check_connection(self, ip: str) -> bool:
        """Verifica si el servidor en la IP especificada responde."""
        try:
            # Intentamos una petición simple al endpoint de status o tags de Ollama
            response = requests.get(f"http://{ip}:11434/api/tags", timeout=5)
            return response.status_code == 200
        except (requests.exceptions.RequestException, Exception):
            return False

    def get_llm(self) -> BaseChatModel:
        """
        Retorna una instancia de ChatOllama si la IP es válida, 
        de lo contrario, inicializa un modelo por defecto vía init_chat_model.
        """
        if self.is_ollama_reachable:
            print(f"Conexión exitosa a Ollama en {self.ip}. Cargando modelo: {self.local_model}")
            return ChatOllama(
                model=self.local_model,
                base_url=f"http://{self.ip}:11434",
                format="json"
            )
        else:
            print(f"Error de conexión en {self.ip}. Cediendo a init_chat_model.")
            return self.get_default_model()

    def get_multimodal_model(self) -> BaseChatModel:
        """
        Provee un modelo multimodal (ejemplo para visión). 
        Sigue la misma lógica de validación de IP que el LLM estándar.
        """
        if self.is_ollama_reachable:
            return ChatOllama(
                model=self.local_model,
                base_url=f"http://{self.ip}:11434"
            )
        else:

            return self.get_default_model()

    def get_default_model(self):
        """Retorna el modelo por defecto usando init_chat_model sin validación de IP específica."""
        return init_chat_model(self.fallback_model)

    def get_embeddings(self):
        """
        Retrieves the appropriate embeddings instance based on connection availability.
        Uses Ollama local embeddings if reachable, and falls back to Gemini embedding model.
        """
        if self.is_ollama_reachable:
            print(f"[ModelProvider] Local Ollama is reachable. Loading local embeddings: {self.local_model}")
            return init_embeddings(
                f"ollama:{self.local_model}",
                base_url=f"http://{self.ip}:11434"
            )
        else:
            print("[ModelProvider] Local Ollama unreachable. Falling back to Google GenAI embeddings.")
            return init_embeddings("google_genai:models/gemini-embedding-2")