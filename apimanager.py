from openai import OpenAI

class APIManager:
    ATTEMPTS = 3
    def __init__(self,api_key):
        self.openai = OpenAI(api_key=api_key)

    # Embeds text into vector, returns None if failed
    def embedText(self, text):
        for i in range(0,APIManager.ATTEMPTS):
            try:
                return self.openai.embeddings.create(input=text, model="text-embedding-3-small")
            except Exception as e:
                print(f"Error embedding text: {str(e)}. Attempt {i+1} of {APIManager.ATTEMPTS}")
        print(f"Failed to embed text through API after {APIManager.ATTEMPTS} attempts.")
        return None
    
    # Query messages, return None if failed
    def query(self, messages):
        for i in range(0,APIManager.ATTEMPTS):
            try:
                return self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
            except Exception as e:
                print(f"Error querying API: {str(e)}. Attempt {i+1} of {APIManager.ATTEMPTS}")
        print(f"Failed to query API for messagesafter {APIManager.ATTEMPTS} attempts.")
        return None
            
