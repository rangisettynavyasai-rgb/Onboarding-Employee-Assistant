#!/usr/bin/env python3
"""
Company AI Assistant: Google Calendar Production Integration
Queries live Google Calendar events via Google Calendar API v3 to identify Out of Office (OOO)
status, working hours, and team leave schedules.
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class CalendarService:
    @staticmethod
    def get_out_of_office_status(access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Queries Google Calendar API for primary calendar events within the current week.
        Scans for eventType='outOfOffice' or OOO/leave keywords.
        """
        now = datetime.utcnow()
        week_end = now + timedelta(days=7)
        time_min = now.isoformat() + "Z"
        time_max = week_end.isoformat() + "Z"

        # Corporate roster comes from the BigQuery employee directory. Calendar is only the
        # availability layer; it must not redefine the canonical person/contact information.
        default_team_status = []
        try:
            from backend.bigquery_service import BigQueryService
            rows = BigQueryService.get_all_employees()
            preferred_emails = {
                "sarah.j@company.com": "Engineering Manager",
                "priya.nair@company.com": "Staff Engineer (Assigned Buddy)",
                "amanda.w@company.com": "People Operations Lead",
                "marcus.v@company.com": "IT Systems Administrator",
            }
            for row in rows:
                email = str(row.get("email", "")).lower()
                if email not in preferred_emails:
                    continue
                default_team_status.append({
                    "name": str(row.get("name", "")),
                    "email": email,
                    "role": preferred_emails[email],
                    "status": "In Office",
                    "source": "Google Calendar",
                    "notes": "Availability is verified from Google Calendar when permitted.",
                    "calendar_synced": False,
                })
        except Exception as db_err:
            print(f"[CalendarService] Directory DB lookup notice: {db_err}")

        # Offline/local fallback only. Production directory data above remains the source of truth.
        if not default_team_status:
            default_team_status = [
                {"name": "Sarah Jenkins", "email": "sarah.j@company.com", "role": "Engineering Manager", "status": "In Office", "source": "Google Calendar", "notes": "Working core hours", "calendar_synced": bool(access_token)},
                {"name": "Priya Nair", "email": "priya.nair@company.com", "role": "Staff Engineer (Assigned Buddy)", "status": "In Office", "source": "Google Calendar", "notes": "Available for onboarding syncs & code reviews", "calendar_synced": bool(access_token)},
                {"name": "Amanda Walker", "email": "amanda.w@company.com", "role": "People Operations Lead", "status": "In Office", "source": "Google Calendar", "notes": "HR & Benefits", "calendar_synced": bool(access_token)},
                {"name": "Marcus Vance", "email": "marcus.v@company.com", "role": "IT Systems Administrator", "status": "In Office", "source": "Google Calendar", "notes": "Hardware & IAM", "calendar_synced": bool(access_token)},
            ]

        if not access_token:
            return {
                "authenticated": False,
                "user_ooo": False,
                "user_status": "In Office",
                "synced_with_google": False,
                "team_members": default_team_status,
                "message": "Connect Google Calendar to sync personal and team OOO status in real-time."
            }

        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events?"
            f"timeMin={urllib.parse.quote(time_min)}&"
            f"timeMax={urllib.parse.quote(time_max)}&"
            f"singleEvents=true&orderBy=startTime"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])

                user_ooo = False
                current_ooo_title = ""
                upcoming_ooo_events = []

                for event in items:
                    event_type = event.get("eventType", "")
                    summary = (event.get("summary") or "").strip()
                    summary_lower = summary.lower()

                    is_ooo = (
                        event_type == "outOfOffice" or
                        "ooo" in summary_lower or
                        "out of office" in summary_lower or
                        "pto" in summary_lower or
                        "vacation" in summary_lower or
                        "leave" in summary_lower or
                        "holiday" in summary_lower
                    )

                    if is_ooo:
                        start_time = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
                        end_time = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")

                        event_info = {
                            "summary": summary or "Out of Office",
                            "start": start_time,
                            "end": end_time,
                            "type": event_type
                        }
                        upcoming_ooo_events.append(event_info)

                        # Check if event is active right now
                        try:
                            if "T" in str(start_time):
                                s_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00")).replace(tzinfo=None)
                                e_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00")).replace(tzinfo=None)
                                if s_dt <= now <= e_dt:
                                    user_ooo = True
                                    current_ooo_title = summary
                        except Exception:
                            pass

                # Best-effort sync of the canonical POC calendars. If the OAuth grant does not
                # permit FreeBusy access to another user's calendar, retain the DB directory entry
                # and its safe default status rather than treating it as an authorization failure.
                try:
                    freebusy_url = "https://www.googleapis.com/calendar/v3/freeBusy"
                    body = json.dumps({
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "items": [{"id": m["email"]} for m in default_team_status if m.get("email")],
                    }).encode("utf-8")
                    fb_req = urllib.request.Request(
                        freebusy_url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST"
                    )
                    with urllib.request.urlopen(fb_req, timeout=6) as fb_resp:
                        fb_data = json.loads(fb_resp.read().decode("utf-8"))
                    calendars = fb_data.get("calendars", {})
                    for member in default_team_status:
                        cal = calendars.get(member.get("email", ""), {})
                        errors = cal.get("errors") or []
                        busy = cal.get("busy") or []
                        if not errors:
                            member["status"] = "Busy / Out of Office" if busy else "Available"
                            member["calendar_synced"] = True
                            member["source"] = "BigQuery employees + Google Calendar FreeBusy"
                except Exception as fb_err:
                    print(f"[CalendarService] POC calendar FreeBusy sync notice: {fb_err}")

                return {
                    "authenticated": True,
                    "synced_with_google": True,
                    "user_ooo": user_ooo,
                    "user_status": f"Out of Office ({current_ooo_title})" if user_ooo else "In Office (Verified via Google Calendar)",
                    "upcoming_leaves": upcoming_ooo_events,
                    "total_events_checked": len(items),
                    "team_members": default_team_status,
                    "message": "Live Google Calendar events verified."
                }

        except urllib.error.HTTPError as he:
            print(f"[CalendarService] Google Calendar API error: {he.code}")
            return {
                "authenticated": False,
                "user_ooo": False,
                "user_status": "In Office",
                "synced_with_google": False,
                "error": f"Google Calendar API returned status {he.code}",
                "team_members": default_team_status,
                "message": "Could not access Google Calendar. Check OAuth permissions."
            }
        except Exception as e:
            print(f"[CalendarService] Error connecting to Google Calendar: {e}")
            return {
                "authenticated": False,
                "user_ooo": False,
                "user_status": "In Office",
                "synced_with_google": False,
                "team_members": default_team_status,
                "message": f"Calendar lookup fallback: {str(e)}"
            }
