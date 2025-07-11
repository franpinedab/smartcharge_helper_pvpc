from datetime import datetime, timedelta
from enum import Enum
import json
from typing import List, Optional, Sequence, Tuple

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData
from pydantic import BaseModel


class ChargingTools(str, Enum):
    GET_BEST_CHARGING_HOURS = "get_best_charging_hours"
    GET_CURRENT_PVPC_PRICES = "get_current_pvpc_prices"


class ChargingRecommendation(BaseModel):
    recommended_hours: List[str]
    average_price_eur_kwh: float
    total_cost_eur: float
    explanation: str
    query_date: str


class HourlyPrice(BaseModel):
    hour: str
    price_eur_kwh: float


class PVPCData(BaseModel):
    date: str
    hourly_prices: List[HourlyPrice]
    min_price: float
    max_price: float
    average_price: float


# Configuration for REE APIDATOS API (no token needed)
REE_BASE_URL = "https://apidatos.ree.es/es/datos"


def create_error(message: str) -> McpError:
    """Helper to create MCP errors with proper ErrorData structure."""
    return McpError(ErrorData(code=-1, message=message))


class ChargingServer:
    """Electric car charging advisor using Spanish PVPC electricity prices."""
    
    async def get_pvpc_prices(self, date: str) -> dict:
        """
        Get PVPC prices for a specific date from REE APIDATOS API.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dict with hourly price data
            
        Raises:
            McpError: If API error or no data available
        """
        start_date = f"{date}T00:00"
        end_date = f"{date}T23:59"
        
        url = f"{REE_BASE_URL}/mercados/precios-mercados-tiempo-real"
        
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "time_trunc": "hour"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
            if response.status_code == 404:
                raise create_error(f"No price data available for date {date}")
            elif response.status_code != 200:
                raise create_error(f"REE API error: {response.status_code}")
                
            data = response.json()
            
            # Verify data exists in response
            if not data.get("included") or len(data["included"]) == 0:
                raise create_error(f"No price data available for date {date}")
                
            # Find PVPC data in response
            pvpc_data = None
            for item in data["included"]:
                if item.get("type") == "PVPC" or "PVPC" in item.get("id", ""):
                    pvpc_data = item
                    break
            
            if not pvpc_data or not pvpc_data.get("attributes", {}).get("values"):
                raise create_error(f"No PVPC data available for date {date}")
                
            return pvpc_data
            
        except httpx.TimeoutException:
            raise create_error("Timeout querying REE API")
        except httpx.RequestError as e:
            raise create_error(f"Connection error with REE API: {str(e)}")
    
    def parse_hourly_prices(self, data: dict) -> List[Tuple[int, float]]:
        """
        Parse REE APIDATOS data and return list of (hour, price).
        
        Args:
            data: JSON response from APIDATOS API
            
        Returns:
            List of tuples (hour_int, price_eur_kwh)
        """
        prices = []
        
        # Data comes in data["attributes"]["values"]
        values = data["attributes"]["values"]
        
        for value in values:
            # Date comes in ISO format: "2024-01-15T00:00:00.000+01:00"
            date_time = datetime.fromisoformat(value["datetime"].replace("Z", "+00:00"))
            hour = date_time.hour
            
            # Price comes in EUR/MWh, convert to EUR/kWh
            price_mwh = value["value"]
            price_kwh = price_mwh / 1000
            
            prices.append((hour, price_kwh))
        
        # Sort by hour to ensure correct order
        prices.sort(key=lambda x: x[0])
        
        return prices
    
    def generate_hour_range(self, start: int, end: int) -> List[int]:
        """
        Generate list of hours considering midnight crossing.
        
        Args:
            start: Start hour (0-23)
            end: End hour (0-23)
            
        Returns:
            List of hours in range
        """
        if start <= end:
            # Normal range (e.g., 8 to 18)
            return list(range(start, end + 1))
        else:
            # Crosses midnight (e.g., 22 to 7)
            return list(range(start, 24)) + list(range(0, end + 1))
    
    def find_best_consecutive_hours(self, prices: List[Tuple[int, float]], 
                                  hour_range: List[int], kwh: float) -> Tuple[List[int], float]:
        """
        Find block of consecutive hours with lowest average price.
        
        Args:
            prices: List of (hour, price)
            hour_range: Valid hours for charging
            kwh: Consumption in kWh (determines how many hours needed)
            
        Returns:
            Tuple (selected_hours, average_price)
        """
        # Filter only hours in allowed range
        filtered_prices = [(h, p) for h, p in prices if h in hour_range]
        
        if not filtered_prices:
            raise create_error("No prices available in specified hour range")
        
        # Determine how many consecutive hours needed
        # For electric cars: assume 7.4kW standard charger
        # hours_needed = ceiling(kwh / charger_power)
        charger_power_kw = 7.4  # Standard AC charger
        hours_needed = max(1, int((kwh / charger_power_kw) + 0.5))  # Round up
        
        # If we need more hours than available, use all available
        if hours_needed > len(filtered_prices):
            hours_needed = len(filtered_prices)
        
        best_avg_price = float('inf')
        best_hours = []
        
        # Search for window of consecutive hours with lowest average price
        for i in range(len(filtered_prices) - hours_needed + 1):
            window = filtered_prices[i:i + hours_needed]
            avg_price = sum(price for _, price in window) / len(window)
            
            if avg_price < best_avg_price:
                best_avg_price = avg_price
                best_hours = [hour for hour, _ in window]
        
        return best_hours, best_avg_price
    
    async def get_best_charging_hours(self, date: Optional[str] = None, 
                                    start_hour: int = 22, end_hour: int = 7, 
                                    kwh: float = 10.0) -> ChargingRecommendation:
        """Get best charging hours for electric car based on PVPC prices."""
        
        # Use current date if not specified
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise create_error("Invalid date format. Use YYYY-MM-DD")
        
        # Get PVPC prices from REE APIDATOS
        pvpc_data = await self.get_pvpc_prices(date)
        hourly_prices = self.parse_hourly_prices(pvpc_data)
        
        # Generate valid hour range
        hour_range = self.generate_hour_range(start_hour, end_hour)
        
        # Find best hours
        best_hours, avg_price = self.find_best_consecutive_hours(
            hourly_prices, hour_range, kwh
        )
        
        # Format hours for response
        formatted_hours = [f"{hour:02d}:00" for hour in best_hours]
        
        # Calculate total cost
        total_cost = kwh * avg_price
        
        # Generate explanation
        if len(best_hours) == 1:
            explanation = (
                f"Recommended charging time: {formatted_hours[0]}. "
                f"With {kwh} kWh consumption, cost will be {total_cost:.2f}€ "
                f"(price: {avg_price:.4f}€/kWh)."
            )
        else:
            start_time = formatted_hours[0]
            end_time = f"{best_hours[-1] + 1:02d}:00"
            explanation = (
                f"Recommended charging period: {start_time} to {end_time}. "
                f"With {kwh} kWh consumption, cost will be {total_cost:.2f}€ "
                f"(average price: {avg_price:.4f}€/kWh)."
            )
        
        return ChargingRecommendation(
            recommended_hours=formatted_hours,
            average_price_eur_kwh=round(avg_price, 4),
            total_cost_eur=round(total_cost, 2),
            explanation=explanation,
            query_date=date
        )
    
    async def get_current_pvpc_prices(self, date: Optional[str] = None) -> PVPCData:
        """Get current PVPC prices for a specific date."""
        
        # Use current date if not specified
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise create_error("Invalid date format. Use YYYY-MM-DD")
        
        # Get PVPC prices from REE APIDATOS
        pvpc_data = await self.get_pvpc_prices(date)
        hourly_prices = self.parse_hourly_prices(pvpc_data)
        
        # Convert to HourlyPrice objects
        price_list = []
        prices_only = []
        
        for hour, price in hourly_prices:
            price_list.append(HourlyPrice(
                hour=f"{hour:02d}:00",
                price_eur_kwh=round(price, 4)
            ))
            prices_only.append(price)
        
        return PVPCData(
            date=date,
            hourly_prices=price_list,
            min_price=round(min(prices_only), 4),
            max_price=round(max(prices_only), 4),
            average_price=round(sum(prices_only) / len(prices_only), 4)
        )


async def serve() -> None:
    """Main MCP server function."""
    server = Server("mcp-charging-advisor")
    charging_server = ChargingServer()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available charging advisor tools."""
        return [
            Tool(
                name=ChargingTools.GET_BEST_CHARGING_HOURS.value,
                description="Get best hours to charge electric car based on Spanish PVPC electricity prices",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (default: today)",
                            "pattern": r"^\d{4}-\d{2}-\d{2}$"
                        },
                        "start_hour": {
                            "type": "integer",
                            "description": "Start hour for charging window (0-23, default: 22)",
                            "minimum": 0,
                            "maximum": 23
                        },
                        "end_hour": {
                            "type": "integer", 
                            "description": "End hour for charging window (0-23, can be < start_hour for midnight crossing, default: 7)",
                            "minimum": 0,
                            "maximum": 23
                        },
                        "kwh": {
                            "type": "number",
                            "description": "Estimated consumption in kWh (default: 10.0)",
                            "minimum": 0.1,
                            "maximum": 100.0
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name=ChargingTools.GET_CURRENT_PVPC_PRICES.value,
                description="Get current Spanish PVPC electricity prices for a specific date",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (default: today)",
                            "pattern": r"^\d{4}-\d{2}-\d{2}$"
                        }
                    },
                    "required": []
                }
            )
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for charging advisor."""
        try:
            match name:
                case ChargingTools.GET_BEST_CHARGING_HOURS.value:
                    result = await charging_server.get_best_charging_hours(
                        date=arguments.get("date"),
                        start_hour=arguments.get("start_hour", 22),
                        end_hour=arguments.get("end_hour", 7),
                        kwh=arguments.get("kwh", 10.0)
                    )

                case ChargingTools.GET_CURRENT_PVPC_PRICES.value:
                    result = await charging_server.get_current_pvpc_prices(
                        date=arguments.get("date")
                    )

                case _:
                    raise create_error(f"Unknown tool: {name}")

            return [
                TextContent(
                    type="text", 
                    text=json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
                )
            ]

        except Exception as e:
            error_msg = f"Error in charging advisor: {str(e)}"
            return [TextContent(type="text", text=error_msg)]
    
    # Run the server
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)
