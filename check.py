try:
    import langchain
    from langchain.memory import VectorStoreRetrieverMemory
    print(f"✅ Sucesso! LangChain localizado em: {langchain.__file__}")
    print(f"✅ Módulo de Memória carregado com sucesso.")
except ImportError as e:
    print(f"❌ Erro de Importação: {e}")
except Exception as e:
    print(f"❌ Outro erro: {e}")