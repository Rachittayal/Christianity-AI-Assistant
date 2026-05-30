import re

BLOCKED   = "blocked"
SENSITIVE = "sensitive"
SAFE      = "safe"

BLOCK_PATTERNS = [

    "rewrite the bible",
    "rewrite genesis",
    "rewrite john",
    "rewrite scripture",
    "rewrite the verse",
    "rewrite this verse",
    "change the bible",
    "modify the bible",
    "edit the bible to say",
    "make the bible say",

    "bible supports nazism",
    "bible supports fascism",
    "bible supports white supremacy",
    "bible supports racism",
    "jesus would have supported hitler",
    "god endorses racial",
    "scripture proves racial",

    "bible says [group] are inferior",
    "god hates gay",
    "god hates jews",
    "god hates muslims",
    "scripture commands killing",
    "bible justifies terrorism",
    "religious justification for violence against",

    "prove god is evil",
    "prove jesus was a fraud",
    "bible is fake",
    "prove the bible supports satanism",
    "write a satanic prayer",
    "prayer to satan",
    "prayer to the devil",
    "demonic prayer",

    "jesus holding a gun",
    "jesus with a weapon",
    "god killing",
    "biblical figure having sex",
    "nude",
    "naked",
    "sexual bible",
]


SENSITIVE_PATTERNS = [

    "why does god allow suffering",
    "why does god allow evil",
    "why do bad things happen",
    "problem of evil",

    "bible and slavery",
    "did god endorse slavery",
    "old testament violence",
    "god commanded genocide",
    "killing in the bible",

    "bible and homosexuality",
    "what does bible say about gay",
    "homosexuality",
    "lgbt and christianity",
    "same sex marriage bible",
    "transgender and bible",

    "is catholicism true christianity",
    "are catholics saved",
    "is orthodoxy correct",
    "which denomination is right",
    "is protestantism heresy",

    "are non-christians going to hell",
    "what happens to people who never heard of jesus",
    "do only christians go to heaven",

    "evolution and christianity",
    "is the earth 6000 years old",
    "dinosaurs and the bible",
    "creation vs evolution",
]


def classify(text: str) -> dict:
    if not text or not text.strip():
        return _result(SAFE, "Empty input", "", text)

    lowered = text.strip().lower()

    for pattern in BLOCK_PATTERNS:
        if pattern in lowered:
            return _result(
                BLOCKED,
                f"Matched block pattern: '{pattern}'",
                _build_block_message(pattern),
                text
            )

    # Check sensitive patterns — process with care
    for pattern in SENSITIVE_PATTERNS:
        if pattern in lowered:
            return _result(
                SENSITIVE,
                f"Matched sensitive pattern: '{pattern}'",
                "",   # no block message — will be processed
                text
            )

    return _result(SAFE, "No patterns matched", "", text)


def _result(status: str, reason: str, message: str, original: str) -> dict:
    return {
        "status":   status,
        "reason":   reason,
        "message":  message,
        "original": original,
    }


def _build_block_message(pattern: str) -> str:
    return (
        "I'm not able to help with that request. "
        "This assistant is designed to support faithful engagement with "
        "Christian scripture and theology. If you have a genuine question "
        "about the Bible or Christian faith, I'm happy to help."
    )


def is_image_request(text: str) -> bool:
    
    lowered = text.strip().lower()

    visual_words = [
        "image", "picture", "photo", "illustration",
        "drawing", "painting", "artwork", "visual", "portrait",
    ]

    subject_indicators = [
        " of ", " showing ", " with ", " depicting ",
        " about ", " featuring ", " for ", " me ",
    ]

    direct_verbs = [
        "draw ", "sketch ", "paint ", "illustrate ",
        "generate ", "create ", "make ", "produce ",
        "show ", "give ", "provide ", "get ",
        "display ", "render ",
    ]

    has_visual_word = any(word in lowered for word in visual_words)

    has_visual_word = any(word in lowered for word in visual_words)
    has_subject = any(ind in lowered for ind in subject_indicators)
    has_direct_verb = any(
        lowered.startswith(verb) or f" {verb}" in lowered
        for verb in direct_verbs
    )

    if has_visual_word and (has_subject or has_direct_verb):
        return True

    if has_direct_verb and has_subject:
        return True

    return False


def classify_image_prompt(prompt: str) -> dict:

    IMAGE_BLOCK_PATTERNS = [
        "jesus holding",
        "jesus carrying a gun",
        "jesus with a flag",
        "jesus endorsing",
        "god endorsing",

        "crucifixion in graphic detail",
        "bloody",
        "gore",

        "nude",
        "naked",
        "sexual",
        "seductive angel",
        "sexy",

        "jesus as a meme",
        "jesus as a joke",
        "funny jesus",
        "mocking jesus",
        "parody of the last supper",

        "jesus with logo",
        "god advertising",
    ]

    lowered = prompt.strip().lower()

    for pattern in IMAGE_BLOCK_PATTERNS:
        if pattern in lowered:
            return _result(
                BLOCKED,
                f"Image prompt matched block pattern: '{pattern}'",
                (
                    "That image cannot be generated. Please request "
                    "a respectful, reverent Christian-themed image."
                ),
                prompt
            )

    return _result(SAFE, "Image prompt passed safety check", "", prompt)