#!/usr/bin/env python3
import anthropic
import os

def create_data_analysis_agent():
    """Create and run an AI data analysis agent"""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    print("🤖 Data Analysis AI Agent")
    print("=" * 50)
    print("Commands:")
    print("  'upload' - Load a data file")
    print("  'ask' - Ask a question about your data")
    print("  'clear' - Clear loaded data")
    print("  'quit' - Exit the agent")
    print("=" * 50)
    
    data_content = ""
    conversation_history = []
    
    while True:
        command = input("\n> Enter command: ").strip().lower()
        
        if command == "quit":
            print("Goodbye!")
            break
        
        elif command == "upload":
            file_path = input("Enter file path (txt, csv, json): ").strip()
            try:
                with open(file_path, 'r') as f:
                    data_content = f.read()
                print(f"✓ Loaded: {file_path} ({len(data_content)} characters)")
            except FileNotFoundError:
                print("❌ File not found!")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif command == "clear":
            data_content = ""
            conversation_history = []
            print("✓ Data cleared")
        
        elif command == "ask":
            if not data_content:
                print("❌ No data loaded. Use 'upload' first.")
                continue
            
            question = input("Ask a question about your data: ").strip()
            if not question:
                continue
            
            # Add user message to history
            conversation_history.append({
                "role": "user",
                "content": question
            })
            
            # Prepare system message with data context
            system_message = f"""You are an expert data analyst. The user has provided you with the following data:

<data>
{data_content}
</data>

Analyze this data carefully and answer user questions with insights, patterns, summaries, and recommendations."""
            
            try:
                print("\n🔍 Analyzing...")
                
                response = client.messages.create(
                    model="claude-opus-4-5-20251101",
                    max_tokens=1000,
                    system=system_message,
                    messages=conversation_history
                )
                
                assistant_response = response.content[0].text
                
                # Add assistant response to history
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                
                print("\n📊 Analysis Result:")
                print("-" * 50)
                print(assistant_response)
                print("-" * 50)
            
            except Exception as e:
                print(f"❌ Error: {e}")
        
        else:
            print("❌ Unknown command. Try 'upload', 'ask', 'clear', or 'quit'")

if __name__ == "__main__":
    create_data_analysis_agent()