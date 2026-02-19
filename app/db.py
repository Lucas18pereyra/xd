from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


class ConfigError(RuntimeError):
    pass


class SupabaseDB:
    def __init__(self, url: str, anon_key: str):
        self.client: Client = create_client(url, anon_key)

    @classmethod
    def from_env(cls) -> "SupabaseDB":
        load_dotenv()
        url = os.getenv("SUPABASE_URL", "").strip()
        anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        if not url or not anon_key:
            raise ConfigError(
                "Faltan variables de entorno: SUPABASE_URL y SUPABASE_ANON_KEY."
            )
        return cls(url, anon_key)

    @staticmethod
    def _normalize_iso_date(value: str) -> str:
        return date.fromisoformat(value).isoformat()

    def sign_up(self, email: str, password: str) -> str:
        self.client.auth.sign_up({"email": email, "password": password})
        return "Cuenta creada. Revisa tu correo si se requiere confirmacion."

    def sign_in(self, email: str, password: str) -> dict[str, str]:
        response = self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        user = getattr(response, "user", None)
        if user is None:
            raise RuntimeError("No se pudo iniciar sesion.")

        user_id = getattr(user, "id", None)
        if not user_id:
            raise RuntimeError("No se pudo obtener el ID del usuario.")

        return {"id": str(user_id), "email": str(getattr(user, "email", email))}

    def sign_out(self) -> None:
        self.client.auth.sign_out()

    def list_habits(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("habits")
            .select("id,name,streak,total_done,last_done_date")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .execute()
        )
        return list(result.data or [])

    def add_habit(self, user_id: str, name: str) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El nombre del habito no puede estar vacio.")
        self.client.table("habits").insert(
            {"user_id": user_id, "name": clean_name}
        ).execute()

    def complete_habit(self, user_id: str, habit_id: int) -> bool:
        today = date.today()
        today_iso = today.isoformat()

        response = (
            self.client.table("habits")
            .select("id,streak,total_done,last_done_date")
            .eq("id", habit_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        if not rows:
            return False

        row = rows[0]
        last_done_value = row.get("last_done_date")
        if last_done_value == today_iso:
            return False

        streak = int(row.get("streak") or 0)
        if last_done_value:
            try:
                last_done_date = date.fromisoformat(str(last_done_value))
            except ValueError:
                new_streak = 1
            else:
                if last_done_date == today - timedelta(days=1):
                    new_streak = streak + 1
                else:
                    new_streak = 1
        else:
            new_streak = 1

        (
            self.client.table("habits")
            .update(
                {
                    "streak": new_streak,
                    "total_done": int(row.get("total_done") or 0) + 1,
                    "last_done_date": today_iso,
                }
            )
            .eq("id", habit_id)
            .eq("user_id", user_id)
            .execute()
        )
        return True

    def delete_habit(self, user_id: str, habit_id: int) -> None:
        (
            self.client.table("habits")
            .delete()
            .eq("id", habit_id)
            .eq("user_id", user_id)
            .execute()
        )

    def list_reminders(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("reminders")
            .select("id,title,due_date")
            .eq("user_id", user_id)
            .order("due_date")
            .order("id")
            .execute()
        )
        return list(result.data or [])

    def add_reminder(self, user_id: str, title: str, due_date: str) -> None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("El titulo no puede estar vacio.")
        due_date_iso = self._normalize_iso_date(due_date)
        self.client.table("reminders").insert(
            {"user_id": user_id, "title": clean_title, "due_date": due_date_iso}
        ).execute()

    def delete_reminder(self, user_id: str, reminder_id: int) -> None:
        (
            self.client.table("reminders")
            .delete()
            .eq("id", reminder_id)
            .eq("user_id", user_id)
            .execute()
        )

    def get_stats(self, user_id: str) -> dict[str, int]:
        habits = self.list_habits(user_id)
        reminders = self.list_reminders(user_id)
        total_habits = len(habits)
        total_done = sum(int(habit.get("total_done") or 0) for habit in habits)
        best_streak = max((int(habit.get("streak") or 0) for habit in habits), default=0)

        return {
            "total_habits": total_habits,
            "total_done": total_done,
            "best_streak": best_streak,
            "total_reminders": len(reminders),
        }
