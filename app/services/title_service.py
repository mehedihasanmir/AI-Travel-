from langchain_openai import ChatOpenAI


def generate_session_title(prompt: str) -> str:
    cleaned = " ".join((prompt or "").strip().split())
    if not cleaned:
        return "New Chat"

    title_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    llm_prompt = (
        "Generate a short chat title from this user prompt. "
        "Rules: 3 to 8 words, plain text only, no quotes, no punctuation at the end.\n"
        f"Prompt: {cleaned}"
    )
    response = title_llm.invoke(llm_prompt)
    title = " ".join(str(response.content or "").strip().split())
    if not title:
        return cleaned[:60].strip() or "New Chat"
    return title[:60].strip()
