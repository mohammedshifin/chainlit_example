from typing import Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import chainlit as cl
import os
import json
from chat_profiles.gpt_3_5_turbo import GPT35Profile
from chat_profiles.gpt_4o import GPT4oProfile
from chat_profiles.gpt_4o_mini import GPT4oMiniProfile


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
    return profiles

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

@cl.on_chat_resume
async def on_chat_resume(thread: Dict[str, Any]):
    user = cl.user_session.get("user")
    chat_profile = cl.user_session.get("chat_profile")

    if not chat_profile:
        await cl.Message(content=f"Welcome back {user.identifier}! Please select a chat profile to continue.").send()
        return

    if isinstance(chat_profile, str):
        chat_profile = cl.ChatProfile(name=chat_profile, markdown_description="")

    message_history = [{"role": "system", "content": "You are a helpful assistant."}]
    root_messages = [m for m in thread["steps"] if m["parentId"] is None]
    
    for msg in root_messages:
        role = "user" if msg["type"] == "user_message" else "assistant"
        message_history.append({
            "role": role,
            "content": msg["output"]
        })

    cl.user_session.set("message_history", message_history)
    model = model_mapping.get(chat_profile.name, chat_profile.name)
    
    # await cl.Message(
    #     content=f"Resumed chat with {user.identifier} using the `{chat_profile.name}` chat profile."
    # ).send()

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

    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}]
    )

    await cl.Message(
        content=f"Starting chat with {user.identifier} using the `{chat_profile.name}` chat profile."
    ).send()
    print(f"Selected chat profile: {chat_profile.name}")
    model = model_mapping.get(chat_profile.name, chat_profile.name)
    print(f"Using model: {model}")

    await cl.Message(content="You can now start sending your messages.").send()

@cl.on_message
async def on_message(message: cl.Message):
    try:
        chat_profile = cl.user_session.get("chat_profile")
        message_history = cl.user_session.get("message_history")
        
        if not chat_profile:
            await cl.Message(content="Error: Chat profile not found.").send()
            return

        if isinstance(chat_profile, str):
            chat_profile = cl.ChatProfile(name=chat_profile, markdown_description="")
        
        if "file" in message.content.lower():
            files = await cl.AskFileMessage(
                content="Please upload a text file.",
                accept=["text/plain"],
                max_size_mb=10
            ).send()
            
            if not files:
                await cl.Message(content="No file was uploaded").send()
                return
                
            text_file = files[0]
            try:
                await cl.Message(content="File was uploaded").send()
                with open(text_file.path, "r", encoding="utf-8") as f:
                    text = f.read()
                user_input = f"{message.content} file content:{text}"
            except Exception as e:
                await cl.Message(content=f"Error reading file:{str(e)}").send()
                return
        else:
            user_input = message.content

        message_history.append({"role": "user", "content": user_input})
        model = model_mapping.get(chat_profile.name, chat_profile.name)
        msg = cl.Message(content="")
        
        stream = await client.chat.completions.create(
            model=model,
            messages=message_history,
            max_tokens=100,
            stream=True
        )

        async for part in stream:
            if token := part.choices[0].delta.content or "":
                await msg.stream_token(token)
                
        message_history.append({"role": "assistant", "content": msg.content})
        await msg.update()

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        await cl.Message(content=error_msg).send()