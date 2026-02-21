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
        url = os.getenv("SUPABASE_URL", "").strip() or "https://rzfesnaawmuncmbyhgwn.supabase.co"
        anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip() or "TU_ANON_LEGACY_AQUI"
        if not url or not anon_key:
            raise ConfigError("Faltan SUPABASE_URL y SUPABASE_ANON_KEY.")
        return cls(url, anon_key)

    def _auth_headers(self, bearer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        return headers

    def _rest_headers(self) -> dict[str, str]:
        if not self.access_token:
            raise RuntimeError("No hay sesión iniciada.")
        return self._auth_headers(self.access_token)

    def sign_up(self, email: str, password: str) -> str:
        response = httpx.post(
            f"{self.url}/auth/v1/signup",
            headers=self._auth_headers(),
            json={"email": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        return "Cuenta creada. Si tu proyecto exige confirmación por email, verifícala antes de iniciar sesión."

    def sign_in(self, email: str, password: str) -> dict[str, str]:
        response = httpx.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._auth_headers(),
            json={"email": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        self.user_id = data["user"]["id"]
        self.user_email = data["user"]["email"]

        return {"id": self.user_id, "email": self.user_email}

    def sign_out(self) -> None:
        self.access_token = None
        self.user_id = None
        self.user_email = None

    def list_habits(self, user_id: str) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.url}/rest/v1/habits",
            headers=self._rest_headers(),
            params={
                "select": "id,name,streak,total_done,last_done_date",
                "user_id": f"eq.{user_id}",
                "order": "id.desc",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def add_habit(self, user_id: str, name: str) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Nombre de hábito vacío.")

        response = httpx.post(
            f"{self.url}/rest/v1/habits",
            headers={**self._rest_headers(), "Prefer": "return=minimal"},
            json={"user_id": user_id, "name": clean_name},
            timeout=30,
        )
        response.raise_for_status()

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
                last_date = date.fromisoformat(last_done)
                new_streak = streak + 1 if last_date == today - timedelta(days=1) else 1
            except ValueError:
                new_streak = 1
        else:
            new_streak = 1

        payload = {
            "streak": new_streak,
            "total_done": int(row.get("total_done") or 0) + 1,
            "last_done_date": today_iso,
        }

        response = httpx.patch(
            f"{self.url}/rest/v1/habits",
            headers={**self._rest_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{habit_id}", "user_id": f"eq.{user_id}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return True

    def delete_habit(self, user_id: str, habit_id: int) -> None:
        response = httpx.delete(
            f"{self.url}/rest/v1/habits",
            headers=self._rest_headers(),
            params={"id": f"eq.{habit_id}", "user_id": f"eq.{user_id}"},
            timeout=30,
        )
        response.raise_for_status()

    def list_reminders(self, user_id: str) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.url}/rest/v1/reminders",
            headers=self._rest_headers(),
            params={
                "select": "id,title,due_date",
                "user_id": f"eq.{user_id}",
                "order": "due_date.asc,id.asc",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def add_reminder(self, user_id: str, title: str, due_date: str) -> None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Título vacío.")
        date.fromisoformat(due_date)

        response = httpx.post(
            f"{self.url}/rest/v1/reminders",
            headers={**self._rest_headers(), "Prefer": "return=minimal"},
            json={"user_id": user_id, "title": clean_title, "due_date": due_date},
            timeout=30,
        )
        response.raise_for_status()

    def delete_reminder(self, user_id: str, reminder_id: int) -> None:
        response = httpx.delete(
            f"{self.url}/rest/v1/reminders",
            headers=self._rest_headers(),
            params={"id": f"eq.{reminder_id}", "user_id": f"eq.{user_id}"},
            timeout=30,
        )
        response.raise_for_status()

    def get_stats(self, user_id: str) -> dict[str, int]:
        habits = self.list_habits(user_id)
        reminders = self.list_reminders(user_id)

        return {
            "total_habits": len(habits),
            "total_done": sum(int(h.get("total_done") or 0) for h in habits),
            "best_streak": max((int(h.get("streak") or 0) for h in habits), default=0),
            "total_reminders": len(reminders),
        }
