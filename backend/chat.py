import os
from dotenv import load_dotenv
from groq import Groq

import safety
import embeddings
import verifier
import image_gen

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

MAX_MEMORY_TURNS = 10
MAX_MESSAGES = MAX_MEMORY_TURNS * 2

RAG_VERSE_COUNT = 5

BASE_SYSTEM_PROMPT = """You are a knowledgeable, pastoral Christian AI assistant grounded in Biblical scripture.

IDENTITY:
- You are warm, respectful, and intellectually honest
- You speak from within the Christian tradition while acknowledging diversity of interpretation
- You treat every question as sincere and deserving of a thoughtful response

SCRIPTURE RULES — CRITICAL:
- Only cite Bible verses you are certain exist
- You will be provided with verified relevant verses in each message — prefer citing those
- If you are uncertain whether a reference exists, say: "I believe this is reflected in [book] around chapter X, but please verify the exact reference"
- Never invent or approximate scripture references
- Never present a paraphrase as a direct quote

DENOMINATION AWARENESS:
- Default to mainstream Protestant/Evangelical perspective
- When topics touch on canon, Mary, saints, sacraments, or salvation — acknowledge that Catholic and Orthodox traditions may differ significantly
- Never declare one denomination superior to others
- Present denominational differences as "tradition A holds X while tradition B holds Y"

SENSITIVE TOPICS:
- Engage honestly with difficult theological questions — do not deflect or refuse
- For theodicy (suffering, evil) — acknowledge the genuine difficulty, present multiple theological frameworks
- For historically complex passages — provide historical and theological context
- Maintain pastoral tone — these questions often come from real pain or genuine seeking

TONE:
- Warm but not sentimental
- Intellectually honest — acknowledge when questions have no simple answers
- Never preachy or condescending
- Concise — give complete answers without unnecessary length"""


SENSITIVE_ADDITION = """

SPECIAL INSTRUCTION FOR THIS RESPONSE:
This question touches on a sensitive or complex theological topic.
- Acknowledge the genuine difficulty or complexity openly
- Present multiple perspectives fairly
- Be pastorally sensitive — the person may be asking from a place of pain or doubt
- Do not give a dismissive or overly simple answer
- End with an invitation for further discussion if appropriate"""

def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "[chat] GROQ_API_KEY not found. Add it to your .env file."
        )
    return Groq(api_key=api_key)



def build_rag_context(verses: list[dict]) -> str:
    if not verses:
        return ""

    lines = ["VERIFIED SCRIPTURE CONTEXT (cite from these preferentially):"]
    for v in verses:
        lines.append(f"  {v['reference']}: {v['text']}")

    return "\n".join(lines)


def build_system_prompt(rag_context: str,is_sensitive: bool,denomination: str = "general") -> str:
    prompt = BASE_SYSTEM_PROMPT

    if is_sensitive:
        prompt += SENSITIVE_ADDITION

    if denomination != "general":
        prompt += f"\n\nDENOMINATION CONTEXT: This user identifies as {denomination}. "
        prompt += f"Frame responses within that tradition while noting significant differences from others."

    if rag_context:
        prompt += f"\n\n{rag_context}"

    return prompt


def trim_memory(messages: list[dict]) -> list[dict]:
    if len(messages) <= MAX_MESSAGES:
        return messages
    return messages[-MAX_MESSAGES:]

def chat(user_message: str,conversation_history: list[dict],denomination: str = "general") -> dict:

    safety_result = safety.classify(user_message)

    if safety_result["status"] == safety.BLOCKED:
        return {
            "type":      "blocked",
            "response":  safety_result["message"],
            "image_url": None,
            "verified":  True,
            "flagged":   [],
            "history":   conversation_history,
            "metadata":  {"blocked_reason": safety_result["reason"]}
        }

    is_sensitive = safety_result["status"] == safety.SENSITIVE

    if safety.is_image_request(user_message):
        image_result = image_gen.generate_image(user_message)

        if image_result["success"]:
            return {
                "type":      "image",
                "response":  "Here is your generated image:",
                "image_url": image_result["image_url"],
                "verified":  True,
                "flagged":   [],
                "history":   conversation_history,
                "metadata":  {
                    "rewritten_prompt": image_result["rewritten_prompt"]
                }
            }
        else:
            return {
                "type":      "text",
                "response":  image_result["message"],
                "image_url": None,
                "verified":  True,
                "flagged":   [],
                "history":   conversation_history,
                "metadata":  {"image_error": image_result["error"]}
            }

    relevant_verses = embeddings.query_similar_verses(user_message,_results=RAG_VERSE_COUNT)
    rag_context = build_rag_context(relevant_verses)

    system_prompt = build_system_prompt(rag_context, is_sensitive, denomination)

    messages = [{"role": "system", "content": system_prompt}]
    messages += conversation_history
    messages += [{"role": "user", "content": user_message}]

    client = get_groq_client()

    llm_response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.7,      
        max_tokens=1024,    
    )

    assistant_text = llm_response.choices[0].message.content

    verification = verifier.verify_text(assistant_text)
    warning_note = verifier.build_warning_note(verification["flagged"])

    final_response = assistant_text
    if warning_note:
        final_response = assistant_text + warning_note

    updated_history = conversation_history + [
        {"role": "user",      "content": user_message},
        {"role": "assistant", "content": final_response},
    ]
    updated_history = trim_memory(updated_history)

    return {
        "type":      "text",
        "response":  final_response,
        "image_url": None,
        "verified":  verification["all_verified"],
        "flagged":   verification["flagged"],
        "history":   updated_history,
        "metadata":  {
            "model":            GROQ_MODEL,
            "verses_retrieved": [v["reference"] for v in relevant_verses],
            "is_sensitive":     is_sensitive,
            "denomination":     denomination,
            "verified_count":   verification["verified_count"],
            "flagged_count":    verification["flagged_count"],
        }
    }
