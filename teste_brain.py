from brain import responder_usuario

print("--- Iniciando Conversa com Aria ---")
try:
    resposta = responder_usuario("Olá! Quem é você?")
    print(f"Aria: {resposta}")
except Exception as e:
    print(f"Erro detectado: {e}")