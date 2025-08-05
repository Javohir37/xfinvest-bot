
import base64
import os
from google import genai
from google.genai import types

prompt = "return just only 0 if the following text is an expense and return just only 1 if it is an investment, if you are not sure just return 0: "


def generate(user_input):
    client = genai.Client(
        api_key="AIzaSyBxgWtRszQJYalspo_0CGFSCS6B96zVxq0",
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt+user_input),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=0,
        ),
        media_resolution="MEDIA_RESOLUTION_MEDIUM",
        tools=tools,
    )
    output = ""
    for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
    ):
        for candidate in chunk.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text"):
                        output += part.text
    print(output)
    return output