import ollama

response = ollama.chat(
    model="qwen3.5:9b",
    messages=[
        {
            "role": "user",
            "content": "Say exactly: Ollama connection is working."
        }
    ],
    think=False
)

print(response["message"]["content"])
