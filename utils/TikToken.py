import constants.ChatOpenAI as ctchat
import tiktoken

class TikToken:
    @classmethod
    def getTokenLength(self, message:str):
        enc = tiktoken.encoding_for_model(ctchat.MODEL_NAME)
        return f"Tokensize:[{len(enc.encode(message))}]"