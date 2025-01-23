from chainlit import ChatProfile

class GPT4oMiniProfile:
    def get_profile(self):
        profile = ChatProfile(
            name="gpt-4o-mini",
            markdown_description="Access to **GPT-4o-mini**",
        )
        return profile
