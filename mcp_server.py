import sys
from mcp.server.stdio import stdio_server
from mcp.server import Server
from scraper import scrape_amazon_top_3

app = Server("shopping-agent-tools")

@app.tool()
async def search_amazon_top_3(query: str) -> str:
    """Searches Amazon for a query and returns the top 3 organic products with reviews data."""
    try:
        products = await scrape_amazon_top_3(query)
        return "[" + ",".join([p.model_dump_json() for p in products]) + "]"
    except Exception as e:
        return f"Error scraping amazon: {e}"

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
