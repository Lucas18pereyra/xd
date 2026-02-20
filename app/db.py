from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import httpx
from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


class SupabaseDB:
    def __init__(self, url: str, anon_key: str):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.access_token: str | None = None
        self.user_id: str | None = None
        self.user_email: str | None = None

    @classmethod
    def from_env(cls) -> "SupabaseDB":
        load_dotenv()
        url = os.getenv("SUPABASE_URL", "").strip()
        anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        if not url or not anon_key:
            raise ConfigError("Faltan SUPABASE_URL y SUPABASE_ANON_KEY.")
        return cls(url, anon_key)

    def _auth_headers(self, bearer: str | None = None) -> dict[str, str]:
        h = {"apikey": self.anon_key, "Content-Type": "application/json"}
        if bearer:
            h["Authorization"] = f"Bearer {bearer}"
        return h

    def sign_up(self, email: str, password: str) -> str:
        r = httpx.post(
            f"{self.url}/auth/v1/signup",
            headers=self._auth_headers(),
            json={"email": email, "password": password},
            timeout=30,
        )
        r.raise_for_status()
        return "Cuenta creada."

    def sign_in(self, email: str, password: str) -> dict[str, str]:
        r = httpx.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._auth_headers(),
            json={"email": email, "password": password},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.access_token = data["access_token"]
        self.user_id = data["user"]["id"]
        self.user_email = data["user"]["email"]
        return {"id": self.user_id, "email": self.user_email}

    def sign_out(self) -> None:
        self.access_token = None
        self.user_id = None
        self.user_email = None

    def _rest_headers(self) -> dict[str, str]:
        if not self.access_token:
            raise RuntimeError("No hay sesión.")
        return self._auth_headers(self.access_token)

    def list_habits(self, user_id: str) -> list[dict[str, Any]]:
        r = httpx.get(
            f"{self.url}/rest/v1/habits",
            headers=self._rest_headers(),
            params={
                "select": "id,name,streak,total_done,last_done_date",
                "user_id": f"eq.{user_id}",
                "order": "id.desc",
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def add_habit(self, user_id: str, name: str) -> None:
        r = httpx.post(
            f"{self.url}/rest/v1/habits",
            headers={**self._rest_headers(), "Prefer": "return=minimal"},
            json={"user_id": user_id, "name": name.strip()},
            timeout=30,
        )
        r.raise_for_status()

    def complete_habit(self, user_id: str, habit_id: int) -> bool:
        rows = self.list_habits(user_id)
        row = next((x for x in rows if int(x["id"]) == habit_id), None)
        if not row:
            return False

        today = date.today()
        today_iso = today.isoformat()
        last_done = row.get("last_done_date")
        if last_done == today_iso:
            return False

        streak = int(row.get("streak") or 0)
        if last_done:
            try:
                last = date.fromisoformat(last_done)
                new_streak = streak + 1 if last == today - timedelta(days=1) else 1
            except ValueError:
                new_streak = 1
        else:
            new_streak = 1

        payload = {
            "streak": new_streak,
            "total_done": int(row.get("total_done") or 0) + 1,
            "last_done_date": today_iso,
        }
        r = httpx.patch(
            f"{self.url}/rest/v1/habits",
            headers={**self._rest_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{habit_id}", "user_id": f"eq.{user_id}"},
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return True

    def delete_habit(self, user_id: str, habit_id: int) -> None:
        r = httpx.delete(
            f"{self.url}/rest/v1/habits",
            headers=self._rest_headers(),
            params={"id": f"eq.{habit_id}", "user_id": f"eq.{user_id}"},
            timeout=30,
        )
        r.raise_for_status()

    def list_reminders(self, user_id: str) -> list[dict[str, Any]]:
        r = httpx.get(
            f"{self.url}/rest/v1/reminders",
            headers=self._rest_headers(),
            params={
                "select": "id,title,due_date",
                "user_id": f"eq.{user_id}",
                "order": "due_date.asc,id.asc",
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def add_reminder(self, user_id: str, title: str, due_date: str) -> None:
        date.fromisoformat(due_date)
        r = httpx.post(
            f"{self.url}/rest/v1/reminders",
            headers={**self._rest_headers(), "Prefer": "return=minimal"},
            json={"user_id": user_id, "title": title.strip(), "due_date": due_date},
            timeout=30,
        )
        r.raise_for_status()

    def delete_reminder(self, user_id: str, reminder_id: int) -> None:
        r = httpx.delete(
            f"{self.url}/rest/v1/reminders",
            headers=self._rest_headers(),
            params={"id": f"eq.{reminder_id}", "user_id": f"eq.{user_id}"},
            timeout=30,
        )
        r.raise_for_status()

    def get_stats(self, user_id: str) -> dict[str, int]:
        habits = self.list_habits(user_id)
        reminders = self.list_reminders(user_id)
        return {
            "total_habits": len(habits),
            "total_done": sum(int(h.get("total_done") or 0) for h in habits),
            "best_streak": max((int(h.get("streak") or 0) for h in habits), default=0),
            "total_reminders": len(reminders),
        }
