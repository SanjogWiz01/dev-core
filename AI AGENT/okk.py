import requests
import json

def chat_with_ai(user_message, conversation_history=[]):
    """
    Send a message to the local AI and get a response
    """
    conversation_history.append({
        'role': 'user',
        'content': user_message
    })
    
    try:
        response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': 'mistral',
                'messages': conversation_history,
                'stream': False
            }
        )
        
        if response.status_code == 200:
            ai_response = response.json()['message']['content']
            conversation_history.append({
                'role': 'assistant',
                'content': ai_response
            })
            return ai_response, conversation_history
        else:
            return "Error: Could not reach AI. Make sure Ollama is running.", conversation_history
    
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to Ollama. Start Ollama first: ollama serve", conversation_history

def main():
    """
    Main chat loop
    """
    print("=" * 50)
    print("Welcome to Your AI Chatbot!")
    print("=" * 50)
    print("Type 'exit' or 'quit' to stop\n")
    
    conversation_history = []
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        
        print("\nAI: Thinking...", end='\r')
        response, conversation_history = chat_with_ai(user_input, conversation_history)
        print("AI:", response)
        print()

if __name__ == "__main__":
    main()