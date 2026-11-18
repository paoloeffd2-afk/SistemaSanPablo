"""Cifrado Fernet (AES + HMAC) de textos sensibles. La clave sale del entorno (RT-01)."""
import os


class Cifrador:
    def __init__(self, clave=None):
        # Se importa aquí (no arriba) para que main.py pueda ofrecer instalar 'cryptography'
        # en vez de cerrarse con un error si todavía no está instalado.
        from cryptography.fernet import Fernet

        clave = clave or os.environ.get("SISTEMA_SAN_PABLO_CLAVE")
        if isinstance(clave, str):
            clave = clave.encode()
        # Sin clave en el entorno se genera una temporal (solo para la demostración).
        self.__fernet = Fernet(clave or Fernet.generate_key())

    def cifrar(self, texto: str) -> bytes:
        return self.__fernet.encrypt(texto.encode("utf-8"))

    def descifrar(self, token: bytes) -> str:
        return self.__fernet.decrypt(token).decode("utf-8")
