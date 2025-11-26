# tools/google/calendar_tools.py
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from .google_apis import create_service

class Calendar(BaseModel):
    id: str = Field(...); name: str = Field(...); time_zone: str = Field(...)
    description: str | None = None

class Calendars(BaseModel):
    count: int; calendars: list[Calendar]; next_page_token: str | None = None

class Attendee(BaseModel):
    email: str; display_name: str | None = None; response_status: str | None = None

class CalendarEvent(BaseModel):
    id: str; name: str; status: str
    description: str | None = None; html_link: str; created: str; updated: str
    organizer_name: str; organizer_email: str; start_time: str; end_time: str
    location: str | None = None; time_zone: str; attendees: list[Attendee] = []

class CalendarEvents(BaseModel):
    count: int; events: list[CalendarEvent]; next_page_token: str | None = None

class CalendarTool:
    API_NAME = "calendar"; API_VERSION = "v3"
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, client_secret_file: str) -> None:
        self.client_secret_file = client_secret_file
        self.service = None
        self.today = datetime.today()
        self.delta = timedelta(days=7)

    def _ensure_service(self) -> None:
        if self.service is None:
            self.service = create_service(
                self.client_secret_file, self.API_NAME, self.API_VERSION, self.SCOPES
            )

    # ---- Calendars
    def list_calendars(self, max_results: int = 10, next_page_token: str | None = None) -> Calendars:
        self._ensure_service()
        records, token = [], next_page_token
        while True:
            resp = self.service.calendarList().list(
                maxResults=min(max_results - len(records), 100), pageToken=token
            ).execute()
            records.extend(resp.get("items", []))
            token = resp.get("nextPageToken")
            if not token or len(records) >= max_results:
                break
        cals = [Calendar(id=r["id"], name=r["summary"], time_zone=r["timeZone"], description=r.get("description"))
                for r in records[:max_results]]
        return Calendars(count=len(cals), calendars=cals, next_page_token=token)

    def create_calendar(self, name: str, time_zone: str = "Europe/Berlin",
                        description: str | None = None) -> Calendar | str:
        self._ensure_service()
        body = {"summary": name, "timeZone": time_zone}
        if description: body["description"] = description
        try:
            r = self.service.calendars().insert(body=body).execute()
            return Calendar(id=r["id"], name=r["summary"], time_zone=r["timeZone"], description=r.get("description"))
        except Exception as e:
            return f"An error occurred: {e}"

    def delete_calendar(self, calendar_id: str) -> str:
        self._ensure_service()
        try:
            self.service.calendars().delete(calendarId=calendar_id).execute()
            return "Calendar deleted"
        except Exception as e:
            return f"An error occurred: {e}"

    def search_calendar(self, name: str, max_results: int = 10,
                        case_sensitive: bool = False, next_page_token: str | None = None) -> Calendars:
        self._ensure_service()
        records, token, left = [], next_page_token, max_results
        while True:
            resp = self.service.calendarList().list(maxResults=min(left, 100), pageToken=token).execute()
            for item in resp.get("items", []):
                src, q = item["summary"], name
                if not case_sensitive: src, q = src.lower(), q.lower()
                if q in src:
                    records.append(item)
                    if len(records) >= max_results: break
            token = resp.get("nextPageToken")
            if len(records) >= max_results or not token: break
            left = max_results - len(records)
        cals = [Calendar(id=r["id"], name=r["summary"], time_zone=r["timeZone"], description=r.get("description"))
                for r in records]
        return Calendars(count=len(cals), calendars=cals, next_page_token=token)

    # ---- Events
    def list_calendar_events(self, calendar_id: str = "primary", max_results: int = 10,
                             time_min: str | None = None, time_max: str | None = None,
                             next_page_token: str | None = None) -> CalendarEvents:
        self._ensure_service()
        time_min = time_min or (self.today - self.delta).isoformat() + "Z"
        time_max = time_max or (self.today + self.delta).isoformat() + "Z"
        records, token = [], next_page_token
        while True:
            resp = self.service.events().list(
                calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                maxResults=min(max_results - len(records), 100), pageToken=token
            ).execute()
            records.extend(resp.get("items", []))
            token = resp.get("nextPageToken")
            if not token or len(records) >= max_results: break
        return CalendarEvents(count=len(records[:max_results]),
                              events=[self._to_event(r) for r in records[:max_results]],
                              next_page_token=token)

    def search_calendar_event(self, query: str, calendar_id: str = "primary", max_results: int = 10,
                              time_min: str | None = None, time_max: str | None = None,
                              next_page_token: str | None = None) -> CalendarEvents:
        self._ensure_service()
        time_min = time_min or (self.today - self.delta).isoformat() + "Z"
        time_max = time_max or (self.today + self.delta).isoformat() + "Z"
        records, token = [], next_page_token
        while True:
            resp = self.service.events().list(
                calendarId=calendar_id, q=query, timeMin=time_min, timeMax=time_max,
                maxResults=min(max_results - len(records), 100), pageToken=token
            ).execute()
            records.extend(resp.get("items", []))
            token = resp.get("nextPageToken")
            if not token or len(records) >= max_results: break
        return CalendarEvents(count=len(records[:max_results]),
                              events=[self._to_event(r) for r in records[:max_results]],
                              next_page_token=token)

    def add_calendar_event(self, name: str, start_time: str, end_time: str,
                           location: str | None = None, description: str | None = None,
                           calendar_id: str = "primary", time_zone: str = "Europe/Berlin") -> CalendarEvent | str:
        self._ensure_service()
        body = {"summary": name, "start": {"dateTime": start_time, "timeZone": time_zone},
                "end": {"dateTime": end_time, "timeZone": time_zone}}
        if description: body["description"] = description
        if location: body["location"] = location
        try:
            r = self.service.events().insert(calendarId=calendar_id, body=body).execute()
            return self._to_event(r, override_tz=time_zone)
        except Exception as e:
            print("⚠️ Google Calendar insert error:", e)
            print("   calendar_id used:", calendar_id)
            raise
            # or: return f"Insert error: {e}"

    def delete_calendar_event(self, calendar_id: str, event_id: str) -> str:
        self._ensure_service()
        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return "Event deleted"
        except Exception as e:
            return f"An error occurred: {e}"

    def update_calendar_event(self, calendar_id: str, event_id: str,
                              name: str | None = None, start_time: str | None = None,
                              end_time: str | None = None, location: str | None = None) -> CalendarEvent | str:
        self._ensure_service()
        body = {}
        if name: body["summary"] = name
        if start_time: body["start"] = {"dateTime": start_time, "timeZone": "America/Chicago"}
        if end_time: body["end"] = {"dateTime": end_time, "timeZone": "America/Chicago"}
        if location: body["location"] = location
        try:
            r = self.service.events().update(calendarId=calendar_id, eventId=event_id, body=body).execute()
            return self._to_event(r)
        except Exception as e:
            return f"An error occurred: {e}"

    def _to_event(self, record: dict, override_tz: str | None = None) -> CalendarEvent:
        start, end = record.get("start", {}), record.get("end", {})
        start_time = start.get("dateTime", start.get("date", ""))
        end_time = end.get("dateTime", end.get("date", ""))
        tz = override_tz or start.get("timeZone") or end.get("timeZone") or ""
        org = record.get("organizer", {})
        attendees = [Attendee(email=a.get("email", ""),
                              display_name=a.get("displayName", ""),
                              response_status=a.get("responseStatus", ""))
                     for a in record.get("attendees", [])]
        return CalendarEvent(
            id=record["id"], name=record.get("summary", ""), status=record.get("status", ""),
            description=record.get("description", ""), html_link=record.get("htmlLink", ""),
            created=record.get("created", ""), updated=record.get("updated", ""),
            organizer_name=org.get("displayName", ""), organizer_email=org.get("email", ""),
            start_time=start_time, end_time=end_time, location=record.get("location", ""),
            time_zone=tz, attendees=attendees
        )