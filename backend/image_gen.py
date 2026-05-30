import re
import requests
from urllib.parse import quote

from safety import classify_image_prompt, BLOCKED

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

IMAGE_WIDTH  = 1024
IMAGE_HEIGHT = 1024

STYLE_SUFFIX = (
    "Byzantine iconography style, Renaissance oil painting aesthetic, "
    "warm golden light, reverent and dignified tone, "
    "historically informed, no modern anachronisms, "
    "no text overlays, museum quality religious art"
)

NEGATIVE_PROMPT = (
    "cartoon, anime, modern clothing, weapons, political symbols, "
    "inappropriate content, offensive, disrespectful, low quality, "
    "blurry, watermark, text"
)

SUBJECT_ENRICHMENTS = {
    "jesus":          "Jesus Christ, compassionate expression, Middle Eastern features, simple robes",
    "christ":         "Jesus Christ, compassionate expression, Middle Eastern features, simple robes",
    "mary":           "the Virgin Mary, gentle expression, blue and white robes, serene",
    "nativity":       "the Nativity scene, baby Jesus in a manger, Mary and Joseph, shepherds, star of Bethlehem",
    "last supper":    "the Last Supper, Jesus and twelve disciples at a long table, dramatic candlelight",
    "crucifixion":    "the crucifixion of Jesus Christ, solemn and reverent, Golgotha, three crosses",
    "resurrection":   "the resurrection of Jesus Christ, empty tomb, radiant light, angels",
    "angel":          "a Biblical angel, traditional iconography, robes of white light, wings, reverent",
    "angels":         "Biblical angels, traditional iconography, robes of white light, wings, reverent",
    "dove":           "a white dove, symbol of the Holy Spirit, soft golden light, peaceful",
    "cross":          "the Christian cross, golden light, stone or wooden, sacred and reverent",
    "garden of eden": "the Garden of Eden, lush paradise, soft morning light, Adam and Eve, peaceful",
    "noah":           "Noah and the Ark, animals, dramatic stormy sky, divine light breaking through",
    "moses":          "Moses, staff, stone tablets, dramatic divine light, desert setting",
    "david":          "King David of Israel, harp, royal robes, Jerusalem, divine favor",
    "baptism":        "the baptism of Jesus by John the Baptist, River Jordan, dove descending, divine light",
    "sermon":         "Jesus delivering the Sermon on the Mount, crowd of followers, hillside setting",
    "prayer":         "a figure in reverent prayer, kneeling, hands clasped, soft divine light",
    "heaven":         "a vision of heaven, golden light, clouds, angels, peaceful and glorious",
    "holy spirit":    "the Holy Spirit as a dove or flame, radiant divine light, sacred and reverent",
}


def rewrite_prompt(user_request: str) -> str:
    
    lowered = user_request.strip().lower()

    triggers_to_strip = [
        "generate an image of",
        "generate image of",
        "create an image of",
        "draw a picture of",
        "draw ",
        "illustrate ",
        "show me an image of",
        "show me a picture of",
        "create a picture of",
        "make an image of",
        "make a picture of",
        "paint a picture of",
        "paint ",
        "artwork of",
        "visual of",
        "generate ",
        "create ",
    ]

    subject = lowered
    for trigger in triggers_to_strip:
        if subject.startswith(trigger):
            subject = subject[len(trigger):].strip()
            break

    enriched = None
    for keyword, description in SUBJECT_ENRICHMENTS.items():
        if keyword in subject:
            enriched = description
            break

    if enriched:
        final_prompt = f"{enriched}, {STYLE_SUFFIX}"
    else:
        final_prompt = f"{subject.capitalize()}, {STYLE_SUFFIX}"

    return final_prompt



def generate_image(user_request: str) -> dict:

    safety_result = classify_image_prompt(user_request)
    if safety_result["status"] == BLOCKED:
        return {
            "success":          False,
            "image_url":        None,
            "rewritten_prompt": None,
            "message":          safety_result["message"],
            "error":            "Blocked by image safety classifier"
        }

    rewritten = rewrite_prompt(user_request)

    encoded_prompt   = quote(rewritten)
    encoded_negative = quote(NEGATIVE_PROMPT)

    url = (
        f"{POLLINATIONS_URL.format(prompt=encoded_prompt)}"
        f"?width={IMAGE_WIDTH}"
        f"&height={IMAGE_HEIGHT}"
        f"&negative={encoded_negative}"
        f"&nologo=true"
        f"&enhance=true"
    )

    try:
        response = requests.get(url, timeout=60)

        if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
            return {
                "success":          True,
                "image_url":        url,
                "rewritten_prompt": rewritten,
                "message":          "Image generated successfully.",
                "error":            None
            }
        else:
            return {
                "success":          False,
                "image_url":        None,
                "rewritten_prompt": rewritten,
                "message":          "Image generation failed. Please try again.",
                "error":            f"HTTP {response.status_code}"
            }

    except requests.Timeout:
        return {
            "success":          False,
            "image_url":        None,
            "rewritten_prompt": rewritten,
            "message":          "Image generation timed out. Please try again.",
            "error":            "Request timeout after 60 seconds"
        }

    except Exception as e:
        return {
            "success":          False,
            "image_url":        None,
            "rewritten_prompt": rewritten,
            "message":          "An unexpected error occurred during image generation.",
            "error":            str(e)
        }
