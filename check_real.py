import sys

print("--- DIAGNÓSTICO DE MEMÓRIA ---")
print(f"Python executando em: {sys.executable}")

try:
    import langchain
    print(f"Versão do LangChain: {langchain.__version__}")
except ImportError:
    print("ERRO: LangChain não está instalado.")

print("\nTentativa 1: langchain.memory")
try:
    from langchain.memory import VectorStoreRetrieverMemory
    print("✅ SUCESSO! Encontrado em: langchain.memory")
except ImportError as e:
    print(f"❌ FALHA em langchain.memory: {e}")

print("\nTentativa 2: langchain_community.memory")
try:
    from langchain_community.memory import VectorStoreRetrieverMemory
    print("✅ SUCESSO! Encontrado em: langchain_community.memory")
except ImportError as e:
    print(f"❌ FALHA em langchain_community.memory: {e}")

print("------------------------------")