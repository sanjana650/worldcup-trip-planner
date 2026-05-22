from fastmcp import FastMCP
from tools import get_matches_by_team

mcp = FastMCP("WorldCupTravelTools")

@mcp.tool()
def get_matches(team: str):
    return get_matches_by_team(team)

if __name__ == "__main__":
    mcp.run()