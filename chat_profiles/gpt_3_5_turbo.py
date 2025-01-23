from chainlit import ChatProfile

class GPT35Profile:
    def get_profile(self):
        profile = ChatProfile(
            name="gpt-3.5-turbo",
            markdown_description="Access to **GPT-3.5-Turbo**",
        )
        return profile
