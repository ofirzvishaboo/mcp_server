import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List

import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
import aiohttp
from dotenv import load_dotenv
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load environment variables
load_dotenv()

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Global variables to store session state
session = None
exit_stack = AsyncExitStack()

# Model configuration
MODEL_ID = "microsoft/phi-2"

# Initialize model and tokenizer
print("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.bfloat16,
    device_map="auto"  # This will automatically handle GPU/CPU placement
)
print("Model and tokenizer loaded successfully!")

async def connect_to_server():
    """Connect to the MCP server."""
    global session, exit_stack

    # Connect to the server using SSE (localhost since we're running client locally)
    sse_transport = await exit_stack.enter_async_context(sse_client("http://localhost:8050/sse"))
    read_stream, write_stream = sse_transport
    session = await exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

    # Initialize the connection
    await session.initialize()

    # List available tools
    tools_result = await session.list_tools()
    print("\nConnected to server with tools:")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")

async def compare_prices(product_name: str) -> str:
    """Compare prices of a product across different websites."""
    global session
    result = await session.call_tool(
        "compare_prices",
        arguments={"product_name": product_name}
    )
    return result.content[0].text

async def get_available_websites() -> str:
    """Get list of available websites for price comparison."""
    global session
    result = await session.call_tool("get_available_websites")
    return result.content[0].text

async def get_ai_analysis(price_data: str) -> str:
    """Get AI analysis of the price comparison data using local model inference."""
    try:
        # Prepare the prompt
        prompt = f"""You are a tech shopping assistant. Analyze this price comparison data and provide insights about the best deals, price differences, and shopping recommendations:

{price_data}

Please provide a concise analysis focusing on:
1. Best value options
2. Price differences between stores
3. Shopping recommendations
4. Any notable deals or savings

Analysis:"""

        # Tokenize the prompt
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        # Generate response
        print("Generating analysis...")
        outputs = model.generate(
            **inputs,
            max_new_tokens=500,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

        # Decode the response
        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
        return response.strip()

    except Exception as e:
        print(f"Debug: Exception details: {str(e)}")
        return f"Error getting AI analysis: {str(e)}"

async def get_shopping_recommendation(product_name: str) -> str:
    """Get AI-powered shopping recommendation for a product."""
    try:
        # First get price comparison data
        price_data = await compare_prices(product_name)

        # Then get AI analysis
        analysis = await get_ai_analysis(price_data)

        return f"Price Comparison:\n{price_data}\n\nAI Analysis:\n{analysis}"
    except Exception as e:
        return f"Error getting recommendation: {str(e)}"

async def cleanup():
    """Clean up resources."""
    global exit_stack
    await exit_stack.aclose()

async def main():
    """Main entry point for the client."""
    try:
        print("Connecting to price comparison server...")
        await connect_to_server()
        print("Connected successfully!")

        while True:
            print("\nTech Shopping Assistant")
            print("1. Compare prices")
            print("2. Get AI shopping recommendation")
            print("3. View available websites")
            print("4. Exit")

            choice = input("\nEnter your choice (1-4): ")

            if choice == "1":
                product_name = input("\nEnter product name to compare: ")
                print("\nFetching prices...")
                result = await compare_prices(product_name)
                print("\nResults:")
                print(result)

            elif choice == "2":
                product_name = input("\nEnter product name for AI recommendation: ")
                print("\nAnalyzing prices and getting AI recommendation...")
                result = await get_shopping_recommendation(product_name)
                print("\nResults:")
                print(result)

            elif choice == "3":
                websites = await get_available_websites()
                print("\nAvailable Websites:")
                print(websites)

            elif choice == "4":
                break

            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())