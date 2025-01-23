from typing import Optional
import chainlit as cl
from openai import OpenAI
from dotenv import load_dotenv
import os 
import json

from chat_profiles.gpt_3_5_turbo import GPT35Profile
from chat_profiles.gpt_4o import GPT4oProfile
from chat_profiles.gpt_4o_mini import GPT4oMiniProfile

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

model_mapping = {
        "GPT-4o": "gpt-4o",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
        "gpt-4o-mini": "gpt-4o-mini"
    } 

def get_chat_profiles():
    """Load chat profiles based on user roles."""
    profiles = []

    profiles.append(GPT35Profile().get_profile())
    profiles.append(GPT4oProfile().get_profile())
    print(profiles)
    return profiles

get_chat_profiles()

@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    role_profiles = get_chat_profiles()

    roles = current_user.metadata.get("role", [])
    if not isinstance(roles, list):
        roles = [roles] 

    profiles = []

    available_profile_names = {profile.name for profile in role_profiles}

    for role in roles:
        if role in available_profile_names:

            for profile in role_profiles:
                if profile.name == role:
                    profiles.append(profile)

    profiles = list({profile.name: profile for profile in profiles}.values())

    return profiles if profiles else None


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    try:
        with open("user_data.json", "r") as f:
            user_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    if username in user_data and user_data[username]["password"] == password:
        return cl.User(identifier=username, metadata={"role": user_data[username]["role"]})
    else:
        return None
    
@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    chat_profile = cl.user_session.get("chat_profile")

    if not chat_profile:
        await cl.Message(
            content=f"Welcome {user.identifier}! You do not have access to any models."
        ).send()
        return

    if isinstance(chat_profile, str):
        chat_profile = cl.ChatProfile(name=chat_profile, markdown_description="")

    await cl.Message(
        content=f"Starting chat with {user.identifier} using the `{chat_profile.name}` chat profile."
    ).send()
    print(f"Selected chat profile: {chat_profile.name}")
    model = model_mapping.get(chat_profile.name,chat_profile.name)  
    print(f"Using model: {model}")

    await cl.Message(content="You can now start sending your messages.").send()

@cl.on_message
async def on_message(message: cl.Message):
    chat_profile = cl.user_session.get("chat_profile")

    if not chat_profile:
        await cl.Message(content="Error: Chat profile not found.").send()
        return

    if isinstance(chat_profile, str):
        chat_profile = cl.ChatProfile(name=chat_profile, markdown_description="")

    
    model = model_mapping.get(chat_profile.name,chat_profile.name)  
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message.content}
        ],
        max_tokens=100
    )

    await cl.Message(
        content=f"Response from {model}: {response.choices[0].message.content}"
    ).send()


