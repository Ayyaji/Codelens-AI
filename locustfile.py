"""Smoke check for the Groq configuration. Does not print the key."""

from rag_core.llm import MODEL_LARGE, MODEL_SMALL, get_api_key


def main():
    print("CodeLens AI — JD-based interview readiness")
    print(f"routing model: {MODEL_SMALL}")
    print(f"explanation model: {MODEL_LARGE}")
    print("GROQ_API_KEY:", "set" if get_api_key() else "missing")


if __name__ == "__main__":
    main()
