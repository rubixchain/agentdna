# host/tools/calendar_adapter.py
from google.adk.tools import FunctionTool
from .gcal.calendar_tools import CalendarTool

_tool = CalendarTool(client_secret_file=".../client-secret.json")

def add_event_tool(
    name: str,
    start_time: str,  
    end_time: str,    
    location: str = "",
    description: str = "",
    calendar_id: str = "primary",
    time_zone: str = "Europe/Berlin",
) -> dict:
    ev = _tool.add_calendar_event(
        name=name,
        start_time=start_time,
        end_time=end_time,
        location=location or None,
        description=description or None,
        calendar_id=calendar_id,
        time_zone=time_zone,
    )
    return ev.model_dump() if hasattr(ev, "model_dump") else ev

def list_calendars_tool(max_results: int = 10) -> dict:
    res = _tool.list_calendars(max_results=max_results)
    return res.model_dump() if hasattr(res, "model_dump") else res

add_event = FunctionTool(add_event_tool)
list_calendars = FunctionTool(list_calendars_tool)