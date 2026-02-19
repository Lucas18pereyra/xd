from __future__ import annotations

from datetime import date

import flet as ft

from app.db import ConfigError, SupabaseDB


BG = "#070b14"
CARD_BG = "#111827"
BORDER = "#263247"
ACCENT = "#4f8cff"
GREEN = "#63d991"
RED = "#ff7a7a"
TEXT_DIM = "#97a6bf"


def main(page: ft.Page) -> None:
    page.title = "Controla Tu Vida"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 16
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.theme = ft.Theme(
        color_scheme_seed=ACCENT,
        visual_density=ft.ThemeVisualDensity.COMPACT,
    )

    root = ft.Column(expand=True, spacing=12, scroll=ft.ScrollMode.AUTO, width=680)
    status = ft.Text(value="", size=13, color=GREEN)
    page.add(root)

    def notify(message: str, color: str = GREEN) -> None:
        status.value = message
        status.color = color

    try:
        db = SupabaseDB.from_env()
    except ConfigError as exc:
        notify(str(exc), RED)
        root.controls = [
            ft.Text("Controla Tu Vida", size=28, weight=ft.FontWeight.W_700),
            ft.Text("Configura Supabase para login y base compartida.", size=13, color=TEXT_DIM),
            status,
            ft.Container(
                bgcolor=CARD_BG,
                border=ft.border.all(1, BORDER),
                border_radius=12,
                padding=12,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Pasos:", weight=ft.FontWeight.W_600),
                        ft.Text("1) Crea un proyecto en Supabase."),
                        ft.Text("2) Ejecuta el SQL de supabase/schema.sql."),
                        ft.Text("3) Define SUPABASE_URL y SUPABASE_ANON_KEY."),
                        ft.Text("4) Reinicia la app."),
                    ],
                ),
            ),
        ]
        page.update()
        return

    current_user_id: str | None = None
    current_user_email = ""

    auth_email = ft.TextField(label="Email", keyboard_type=ft.KeyboardType.EMAIL, autofocus=True)
    auth_password = ft.TextField(label="Contrasena", password=True, can_reveal_password=True)

    habit_name = ft.TextField(label="Nuevo habito", hint_text="Leer, entrenar, meditar...", filled=True)
    habits_list = ft.Column(spacing=8)

    reminder_title = ft.TextField(label="Titulo recordatorio", filled=True)
    reminder_date = ft.TextField(label="Fecha", hint_text="YYYY-MM-DD", value=date.today().isoformat(), filled=True)
    reminders_list = ft.Column(spacing=8)

    stats_col = ft.Column(spacing=6)
    user_badge = ft.Text(value="", size=12, color=TEXT_DIM)

    def error_text(exc: Exception) -> str:
        text = str(exc).strip()
        return text or "Operacion fallida."

    def refresh_habits() -> None:
        if not current_user_id:
            habits_list.controls = []
            return

        rows = db.list_habits(current_user_id)
        if not rows:
            habits_list.controls = [ft.Text("No hay habitos todavia.", color=TEXT_DIM)]
            return

        controls: list[ft.Control] = []
        for row in rows:
            habit_id = int(row["id"])
            controls.append(
                ft.Container(
                    bgcolor=CARD_BG,
                    border=ft.border.all(1, BORDER),
                    border_radius=12,
                    padding=10,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(str(row["name"]), size=16, weight=ft.FontWeight.W_600),
                                    ft.Text(
                                        f"Racha: {int(row['streak'] or 0)} | Hecho: {int(row['total_done'] or 0)}",
                                        size=12,
                                        color=TEXT_DIM,
                                    ),
                                ],
                            ),
                            ft.Row(
                                spacing=0,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                        icon_color=GREEN,
                                        tooltip="Completar hoy",
                                        on_click=lambda e, hid=habit_id: on_complete_habit(hid),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=RED,
                                        tooltip="Eliminar",
                                        on_click=lambda e, hid=habit_id: on_delete_habit(hid),
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )
        habits_list.controls = controls

    def refresh_reminders() -> None:
        if not current_user_id:
            reminders_list.controls = []
            return

        rows = db.list_reminders(current_user_id)
        if not rows:
            reminders_list.controls = [ft.Text("No hay recordatorios todavia.", color=TEXT_DIM)]
            return

        controls: list[ft.Control] = []
        for row in rows:
            reminder_id = int(row["id"])
            controls.append(
                ft.Container(
                    bgcolor=CARD_BG,
                    border=ft.border.all(1, BORDER),
                    border_radius=12,
                    padding=10,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(str(row["title"]), size=15, weight=ft.FontWeight.W_600),
                                    ft.Text(f"Fecha: {row['due_date']}", size=12, color=TEXT_DIM),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=RED,
                                tooltip="Eliminar",
                                on_click=lambda e, rid=reminder_id: on_delete_reminder(rid),
                            ),
                        ],
                    ),
                )
            )
        reminders_list.controls = controls

    def refresh_stats() -> None:
        if not current_user_id:
            stats_col.controls = []
            return

        stats = db.get_stats(current_user_id)
        stats_col.controls = [
            ft.Container(
                bgcolor=CARD_BG,
                border=ft.border.all(1, BORDER),
                border_radius=12,
                padding=12,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text(f"Total habitos: {stats['total_habits']}", size=15),
                        ft.Text(f"Total completados: {stats['total_done']}", size=15),
                        ft.Text(f"Mejor racha: {stats['best_streak']}", size=15),
                        ft.Text(f"Total recordatorios: {stats['total_reminders']}", size=15),
                    ],
                ),
            ),
        ]

    def refresh_all() -> None:
        refresh_habits()
        refresh_reminders()
        refresh_stats()

    def on_add_habit(_: ft.ControlEvent) -> None:
        if not current_user_id:
            notify("Inicia sesion primero.", RED)
            page.update()
            return

        name = (habit_name.value or "").strip()
        if not name:
            notify("Escribe el nombre del habito.", RED)
            page.update()
            return

        try:
            db.add_habit(current_user_id, name)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        habit_name.value = ""
        notify("Habito agregado.")
        refresh_all()
        page.update()

    def on_complete_habit(habit_id: int) -> None:
        if not current_user_id:
            notify("Inicia sesion primero.", RED)
            page.update()
            return

        try:
            ok = db.complete_habit(current_user_id, habit_id)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        if ok:
            notify("Habito completado hoy.")
        else:
            notify("Ya estaba completado hoy.", RED)
        refresh_all()
        page.update()

    def on_delete_habit(habit_id: int) -> None:
        if not current_user_id:
            notify("Inicia sesion primero.", RED)
            page.update()
            return

        try:
            db.delete_habit(current_user_id, habit_id)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        notify("Habito eliminado.")
        refresh_all()
        page.update()

    def on_add_reminder(_: ft.ControlEvent) -> None:
        if not current_user_id:
            notify("Inicia sesion primero.", RED)
            page.update()
            return

        title = (reminder_title.value or "").strip()
        due = (reminder_date.value or "").strip()
        if not title:
            notify("Escribe un titulo.", RED)
            page.update()
            return

        try:
            db.add_reminder(current_user_id, title, due)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        reminder_title.value = ""
        reminder_date.value = date.today().isoformat()
        notify("Recordatorio agregado.")
        refresh_all()
        page.update()

    def on_delete_reminder(reminder_id: int) -> None:
        if not current_user_id:
            notify("Inicia sesion primero.", RED)
            page.update()
            return

        try:
            db.delete_reminder(current_user_id, reminder_id)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        notify("Recordatorio eliminado.")
        refresh_all()
        page.update()

    def on_sign_up(_: ft.ControlEvent) -> None:
        email = (auth_email.value or "").strip()
        password = auth_password.value or ""
        if not email or not password:
            notify("Completa email y contrasena.", RED)
            page.update()
            return

        try:
            message = db.sign_up(email, password)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        notify(message)
        page.update()

    def on_sign_in(_: ft.ControlEvent) -> None:
        nonlocal current_user_id, current_user_email

        email = (auth_email.value or "").strip()
        password = auth_password.value or ""
        if not email or not password:
            notify("Completa email y contrasena.", RED)
            page.update()
            return

        try:
            user = db.sign_in(email, password)
        except Exception as exc:
            notify(error_text(exc), RED)
            page.update()
            return

        current_user_id = user["id"]
        current_user_email = user["email"]
        user_badge.value = f"Usuario: {current_user_email}"
        refresh_all()
        notify("Sesion iniciada.")
        render()

    def on_sign_out(_: ft.ControlEvent) -> None:
        nonlocal current_user_id, current_user_email

        try:
            db.sign_out()
        except Exception:
            pass

        current_user_id = None
        current_user_email = ""
        user_badge.value = ""
        notify("Sesion cerrada.")
        render()

    tabs = ft.Tabs(
        selected_index=0,
        expand=True,
        tabs=[
            ft.Tab(
                text="Habitos",
                content=ft.Container(
                    padding=10,
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            habit_name,
                            ft.ElevatedButton(
                                "Agregar habito",
                                icon=ft.Icons.ADD,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=12),
                                on_click=on_add_habit,
                            ),
                            ft.Divider(height=4, color="transparent"),
                            habits_list,
                        ],
                    ),
                ),
            ),
            ft.Tab(
                text="Recordatorios",
                content=ft.Container(
                    padding=10,
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            reminder_title,
                            reminder_date,
                            ft.ElevatedButton(
                                "Agregar recordatorio",
                                icon=ft.Icons.NOTIFICATIONS_ACTIVE,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=12),
                                on_click=on_add_reminder,
                            ),
                            ft.Divider(height=4, color="transparent"),
                            reminders_list,
                        ],
                    ),
                ),
            ),
            ft.Tab(
                text="Estadisticas",
                content=ft.Container(
                    padding=10,
                    content=stats_col,
                ),
            ),
        ],
    )

    auth_card = ft.Container(
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER),
        border_radius=16,
        padding=16,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text("Bienvenido", size=22, weight=ft.FontWeight.W_700),
                ft.Text("Inicia sesion para entrar a tus habitos.", size=13, color=TEXT_DIM),
                auth_email,
                auth_password,
                ft.ElevatedButton(
                    "Iniciar sesion",
                    icon=ft.Icons.LOGIN,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=12),
                    on_click=on_sign_in,
                ),
                ft.OutlinedButton(
                    "Crear cuenta",
                    icon=ft.Icons.PERSON_ADD,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=12),
                    on_click=on_sign_up,
                ),
            ],
        ),
    )

    def render() -> None:
        if current_user_id:
            root.controls = [
                ft.Container(
                    border_radius=18,
                    padding=16,
                    gradient=ft.LinearGradient(colors=["#163a78", "#0d2145"], begin=ft.alignment.top_left, end=ft.alignment.bottom_right),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text("Controla Tu Vida", size=28, weight=ft.FontWeight.W_700),
                                    user_badge,
                                ],
                            ),
                            ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="Cerrar sesion", on_click=on_sign_out),
                        ],
                    ),
                ),
                status,
                tabs,
            ]
        else:
            root.controls = [
                ft.Text("Controla Tu Vida", size=28, weight=ft.FontWeight.W_700),
                ft.Text("App movil online con login y base compartida.", size=13, color=TEXT_DIM),
                status,
                auth_card,
            ]
        page.clean()
        page.add(ft.Row([root], alignment=ft.MainAxisAlignment.CENTER))
        page.update()

    render()


if __name__ == "__main__":
    ft.app(target=main)
