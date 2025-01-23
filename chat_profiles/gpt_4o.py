from chainlit import ChatProfile

class GPT4oProfile:
    def get_profile(self):
        profile = ChatProfile(
            name="gpt-4o",
            markdown_description="Access to **GPT-4o**",
        )
        return profile
