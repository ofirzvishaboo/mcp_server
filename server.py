import asyncio
import json
from typing import Dict, List, Optional, Union
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup, Tag
import random
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP(
    name="Tech Price Comparator",
    host="0.0.0.0",
    port=8050,
)

def find_element(soup: BeautifulSoup, selector: Union[str, Dict[str, str]]) -> Optional[Tag]:
    """
    Find an element using various selector types.
    selector can be:
    - A string (CSS selector)
    - A dict with keys: 'class', 'id', 'tag', 'attrs'
    """
    if isinstance(selector, str):
        return soup.select_one(selector)

    if isinstance(selector, dict):
        if 'class' in selector:
            return soup.find(class_=selector['class'])
        if 'id' in selector:
            return soup.find(id=selector['id'])
        if 'tag' in selector:
            return soup.find(selector['tag'])
        if 'attrs' in selector:
            return soup.find(attrs=selector['attrs'])

    return None

# Website configurations
WEBSITES = {
    "amazon": {
        "url": "https://www.amazon.com/s?k={}",
        "price_selector": {
            "class": "a-price-whole"
        },
        "name_selector": {
            "class": "a-size-medium"
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    },
    "bestbuy": {
        "url": "https://www.bestbuy.com/site/searchpage.jsp?st={}",
        "price_selector": {
            "class": "priceView-customer-price"
        },
        "name_selector": {
            "tag": "h4",
            "attrs": {"class": "sku-title"}
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    },
    "newegg": {
        "url": "https://www.newegg.com/p/pl?d={}",
        "price_selector": {
            "class": "price-current"
        },
        "name_selector": {
            "tag": "a",
            "attrs": {"class": "item-title"}
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    }
}

async def fetch_price(session: aiohttp.ClientSession, website: str, product_name: str) -> Optional[Dict]:
    """Fetch price from a specific website."""
    try:
        config = WEBSITES[website]
        url = config["url"].format(product_name.replace(" ", "+"))

        # Add a random delay between 1-3 seconds
        await asyncio.sleep(random.uniform(1, 3))

        # Set a timeout of 10 seconds for the request
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, headers=config["headers"], timeout=timeout) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find the first product using the modular find_element function
                price_element = find_element(soup, config["price_selector"])
                name_element = find_element(soup, config["name_selector"])

                if price_element and name_element:
                    # Clean up price text
                    price_text = price_element.text.strip()
                    price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_text)))

                    return {
                        "website": website,
                        "name": name_element.text.strip(),
                        "price": price,
                        "url": url,
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                print(f"Failed to fetch page from {website}. Status code: {response.status}")
    except asyncio.TimeoutError:
        print(f"Request timed out for {website}")
    except Exception as e:
        print(f"Error fetching from {website}: {str(e)}")
    return None

@mcp.tool()
async def compare_prices(product_name: str) -> str:
    """Compare prices of a tech product across different websites.

    Args:
        product_name: Name of the product to search for.

    Returns:
        A formatted string containing price comparisons.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch prices from all websites concurrently
            tasks = [fetch_price(session, website, product_name) for website in WEBSITES]
            results = await asyncio.gather(*tasks)

            # Filter out None results
            valid_results = [r for r in results if r is not None]

            if not valid_results:
                return f"No prices found for {product_name}"

            # Sort by price
            valid_results.sort(key=lambda x: x["price"])

            # Format the results
            output = f"Price Comparison for: {product_name}\n\n"
            output += "Best Prices:\n"

            for i, result in enumerate(valid_results, 1):
                output += f"\n{i}. {result['website'].title()}:\n"
                output += f"   Product: {result['name']}\n"
                output += f"   Price: ${result['price']:.2f}\n"
                output += f"   URL: {result['url']}\n"

            # Add summary
            best_price = valid_results[0]
            output += f"\nBest Deal: {best_price['website'].title()} at ${best_price['price']:.2f}\n"
            output += f"Price Range: ${valid_results[0]['price']:.2f} - ${valid_results[-1]['price']:.2f}\n"
            output += f"Number of stores compared: {len(valid_results)}\n"

            return output

    except Exception as e:
        return f"Error comparing prices: {str(e)}"

@mcp.tool()
async def get_available_websites() -> str:
    """Get list of available websites for price comparison."""
    return "Available websites for price comparison:\n" + "\n".join(f"- {site}" for site in WEBSITES.keys())

# Run the server
if __name__ == "__main__":
    print("Running Tech Price Comparator server with SSE transport")
    mcp.run(transport="sse")