from tools.gcal import CalendarTool
import os

os.environ["GOOGLE_CLIENT_SECRET"] = "/Users/rameshsubramani/Desktop/Desktop/mcp_calendar/client-secret.json"
# optionally: os.environ["GOOGLE_TOKEN_DIR"] = "/absolute/path/to/token files"

cal = CalendarTool(os.environ["GOOGLE_CLIENT_SECRET"])
print(cal.list_calendars(max_results=5).model_dump())