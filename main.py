from kivy.lang import Builder
Builder.load_file("sakayko_ui.kv")

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivy.clock import Clock
from database import (
    create_tables, register_user, login_user,
    submit_waiting, cancel_waiting, get_active_requests,
    get_fuel_price, get_today_summary, get_recommendations,
    STOP_NAMES, compute_fare, get_stops_between,
    log_multi_stop_trip, get_daily_history, clear_today
)
from fuel_fetcher import get_latest_fuel_price
from lang import t, set_lang, get_lang


def refresh_all_screens(sm):
    for screen in sm.screens:
        if hasattr(screen, "refresh_lang"):
            screen.refresh_lang()


class SplashScreen(Screen):
    tagline = StringProperty("")
    def on_enter(self): self.refresh_lang()
    def refresh_lang(self): self.tagline = t("tagline")


class LoginScreen(Screen):
    title_text  = StringProperty("")
    sub_text    = StringProperty("")
    email_lbl   = StringProperty("")
    pass_lbl    = StringProperty("")
    btn_text    = StringProperty("")
    no_acc_text = StringProperty("")
    reg_text    = StringProperty("")

    def on_enter(self): self.refresh_lang()
    def refresh_lang(self):
        self.title_text  = t("login_title")
        self.sub_text    = t("login_sub")
        self.email_lbl   = t("email")
        self.pass_lbl    = t("password")
        self.btn_text    = t("sign_in")
        self.no_acc_text = t("no_account")
        self.reg_text    = t("register_link")

    def toggle_lang(self):
        set_lang("tl" if get_lang() == "en" else "en")
        refresh_all_screens(self.manager)

    def do_login(self):
        email    = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()
        if not email or not password:
            self.show_dialog("Error", "Please fill in all fields." if get_lang()=="en" else "Punan ang lahat ng fields.")
            return
        success, result = login_user(email, password)
        if success:
            app = MDApp.get_running_app()
            app.current_user = result
            self.manager.current = "driver_home" if result["role"] == "driver" else "passenger_home"
        else:
            self.show_dialog("Login Failed" if get_lang()=="en" else "Mali ang login", result)

    def show_dialog(self, title, message):
        d = MDDialog(title=title, text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()


class RegisterScreen(Screen):
    title_text    = StringProperty("")
    sub_text      = StringProperty("")
    name_lbl      = StringProperty("")
    email_lbl     = StringProperty("")
    pass_lbl      = StringProperty("")
    btn_text      = StringProperty("")
    have_acc      = StringProperty("")
    login_lnk     = StringProperty("")
    driver_lbl    = StringProperty("")
    pass_lbl2     = StringProperty("")
    selected_role = StringProperty("driver")

    def on_enter(self): self.refresh_lang()
    def refresh_lang(self):
        self.title_text = t("register_title")
        self.sub_text   = t("register_sub")
        self.name_lbl   = t("full_name")
        self.email_lbl  = t("email")
        self.pass_lbl   = t("password_hint")
        self.btn_text   = t("create_account")
        self.have_acc   = t("have_account")
        self.login_lnk  = t("login_link")
        self.driver_lbl = t("driver_btn")
        self.pass_lbl2  = t("passenger_btn")

    def select_role(self, role): self.selected_role = role

    def do_register(self):
        name     = self.ids.name_input.text.strip()
        email    = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()
        if not name or not email or not password:
            self.show_dialog("Error", "Please fill in all fields." if get_lang()=="en" else "Punan ang lahat ng fields.")
            return
        if len(password) < 6:
            self.show_dialog("Error", "Password must be at least 6 characters." if get_lang()=="en" else "Dapat 6 characters ang password.")
            return
        success, message = register_user(name, email, password, self.selected_role)
        if success:
            self.show_dialog("Success" if get_lang()=="en" else "Tagumpay",
                "Account created! You can now log in." if get_lang()=="en" else "Nagawa na ang account!")
            self.manager.current = "login"
        else:
            self.show_dialog("Error", message)

    def show_dialog(self, title, message):
        d = MDDialog(title=title, text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()


class PassengerHomeScreen(Screen):
    status_text   = StringProperty("")
    passenger_lbl = StringProperty("")
    select_lbl    = StringProperty("")
    wait_btn_text = StringProperty("")
    how_title     = StringProperty("")
    how_body      = StringProperty("")
    logout_text   = StringProperty("")
    is_waiting    = False

    def on_enter(self):
        self.refresh_lang()
        self.ids.stop_spinner.values = STOP_NAMES
        self.ids.stop_spinner.text   = STOP_NAMES[0]

    def refresh_lang(self):
        self.passenger_lbl = t("passenger_label")
        self.select_lbl    = t("select_stop")
        self.how_title     = t("how_title")
        self.how_body      = t("how_body")
        self.logout_text   = t("logout")
        if not self.is_waiting:
            self.status_text   = t("status_default")
            self.wait_btn_text = t("waiting_btn")
        else:
            self.wait_btn_text = t("cancel_btn")

    def toggle_waiting(self):
        app     = MDApp.get_running_app()
        user_id = app.current_user["id"]
        if not self.is_waiting:
            stop = self.ids.stop_spinner.text
            submit_waiting(user_id, stop)
            self.is_waiting    = True
            self.status_text   = t("visible_at") + stop
            self.wait_btn_text = t("cancel_btn")
            self.ids.wait_btn.md_bg_color = (0.8, 0.1, 0.1, 1)
        else:
            cancel_waiting(user_id)
            self.is_waiting    = False
            self.status_text   = t("status_default")
            self.wait_btn_text = t("waiting_btn")
            self.ids.wait_btn.md_bg_color = (1, 0.72, 0, 1)

    def do_logout(self):
        app = MDApp.get_running_app()
        if self.is_waiting:
            cancel_waiting(app.current_user["id"])
            self.is_waiting = False
        app.current_user = {}
        self.manager.current = "login"


class DriverHomeScreen(Screen):
    fuel_price    = NumericProperty(0.0)
    fuel_source   = StringProperty("loading...")
    total_income  = NumericProperty(0.0)
    total_fuel    = NumericProperty(0.0)
    total_net     = NumericProperty(0.0)
    trip_count    = NumericProperty(0)
    trip_summary  = StringProperty("")
    income_lbl    = StringProperty("")
    fuel_lbl      = StringProperty("")
    net_lbl       = StringProperty("")
    gas_lbl       = StringProperty("")
    trips_lbl     = StringProperty("")
    waiting_sec   = StringProperty("")
    trip_ttl      = StringProperty("")
    from_lbl      = StringProperty("")
    to_lbl        = StringProperty("")
    trip_hint_txt = StringProperty("")
    start_txt     = StringProperty("")
    complete_txt  = StringProperty("")
    tips_txt      = StringProperty("")
    logout_txt    = StringProperty("")
    new_day_txt   = StringProperty("")
    history_txt   = StringProperty("")

    driver_lbl   = StringProperty("DRIVER")

    _trip_from   = ""
    _trip_to     = ""
    _passengers  = {}
    _trip_active = False

    def on_enter(self):
        self.refresh_lang()
        self.ids.from_spinner.values = STOP_NAMES
        self.ids.from_spinner.text   = STOP_NAMES[0]
        self.ids.to_spinner.values   = STOP_NAMES
        self.ids.to_spinner.text     = STOP_NAMES[-1]
        self.refresh_data()
        Clock.schedule_once(lambda dt: self.fetch_fuel_price(), 1)
        Clock.schedule_interval(self.auto_refresh, 10)

    def on_leave(self):
        Clock.unschedule(self.auto_refresh)

    def refresh_lang(self):
        self.driver_lbl    = t("driver_label")
        self.income_lbl    = t("income_lbl")
        self.fuel_lbl      = t("fuel_lbl")
        self.net_lbl       = t("net_lbl")
        self.gas_lbl       = t("gas_lbl")
        self.trips_lbl     = t("trips_lbl")
        self.waiting_sec   = t("waiting_section")
        self.trip_ttl      = t("trip_card_title")
        self.from_lbl      = t("from_lbl")
        self.to_lbl        = t("to_lbl")
        self.trip_hint_txt = t("trip_hint") if not self.trip_summary else self.trip_summary
        self.start_txt     = t("start_btn")
        self.complete_txt  = t("complete_btn")
        self.tips_txt      = t("tips_btn")
        self.logout_txt    = t("logout")
        self.new_day_txt   = t("new_day_btn")
        self.history_txt   = t("history_btn")

    def auto_refresh(self, dt): self.refresh_data()

    def fetch_fuel_price(self):
        try:
            price, source    = get_latest_fuel_price()
            self.fuel_price  = price
            self.fuel_source = source
        except Exception:
            self.fuel_price  = get_fuel_price()
            self.fuel_source = "cached"

    def refresh_data(self):
        app = MDApp.get_running_app()
        self.fuel_price = get_fuel_price()
        requests = get_active_requests()
        summary  = get_today_summary(app.current_user["id"])
        self.total_income = summary["total_income"]
        self.total_fuel   = summary["total_fuel"]
        self.total_net    = summary["total_net"]
        self.trip_count   = summary["trip_count"]

        self.ids.passenger_list.clear_widgets()
        if not requests:
            from kivymd.uix.label import MDLabel
            self.ids.passenger_list.add_widget(MDLabel(
                text=t("no_waiting"), halign="center",
                theme_text_color="Secondary",
                size_hint_y=None, height="40dp"))
        else:
            from kivymd.uix.card import MDCard
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.label import MDLabel
            from kivy.metrics import dp
            for r in requests:
                card = MDCard(size_hint_y=None, height=dp(56),
                    padding=dp(10), md_bg_color=(0.93, 0.95, 1.0, 1), radius=[10])
                box = MDBoxLayout(orientation="horizontal")
                left = MDBoxLayout(orientation="vertical")
                left.add_widget(MDLabel(text=r["stop_name"],
                    font_style="Subtitle2", bold=True, theme_text_color="Primary"))
                left.add_widget(MDLabel(
                    text=f"{r['passenger_count']} {'naghihintay' if get_lang()=='tl' else 'waiting'}",
                    font_style="Caption", theme_text_color="Secondary"))
                box.add_widget(left)
                box.add_widget(MDLabel(text=str(r["passenger_count"]),
                    halign="right", theme_text_color="Custom",
                    text_color=(1, 0.72, 0, 1), font_style="H5", bold=True))
                card.add_widget(box)
                self.ids.passenger_list.add_widget(card)

    def start_trip(self):
        frm = self.ids.from_spinner.text
        to  = self.ids.to_spinner.text
        if frm == to:
            self.show_dialog("Error",
                "From and To must be different." if get_lang()=="en" else "Magkaiba dapat ang Mula at Patungo.")
            return
        stops = get_stops_between(frm, to)
        if not stops:
            self.show_dialog("Error", "Invalid route." if get_lang()=="en" else "Hindi valid ang ruta.")
            return
        self._trip_from   = frm
        self._trip_to     = to
        self._passengers  = {s: 0 for s in stops}
        self._trip_active = True
        self.trip_summary  = f"{t('trip_active')}{frm} → {to}"
        self.trip_hint_txt = self.trip_summary
        self._rebuild_stop_rows(stops)
        self.ids.start_trip_btn.disabled    = True
        self.ids.complete_trip_btn.disabled = False
        self.ids.from_spinner.disabled      = True
        self.ids.to_spinner.disabled        = True

    def _rebuild_stop_rows(self, stops):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDRaisedButton
        from kivy.uix.textinput import TextInput
        from kivy.metrics import dp
        container = self.ids.stop_rows
        container.clear_widgets()
        self._stop_inputs = {}
        for stop in stops:
            fare, dist = compute_fare(self._trip_from, stop)
            row = MDBoxLayout(orientation="horizontal",
                size_hint_y=None, height=dp(46), spacing=dp(6))
            lbl = MDLabel(
                text=f"{stop}\n₱{fare:.0f} · {dist:.1f}km",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=(0.01, 0.19, 0.53, 1),
                size_hint_x=0.45)
            minus_btn = MDRaisedButton(text="−",
                size_hint_x=None, width=dp(38), height=dp(38),
                md_bg_color=(0.8, 0.1, 0.1, 1), font_size="18sp")
            ti = TextInput(text="0", multiline=False, input_filter="int",
                font_size="15sp", halign="center", size_hint_x=0.18,
                background_color=(0.93, 0.95, 1.0, 1),
                foreground_color=(0.01, 0.19, 0.53, 1))
            plus_btn = MDRaisedButton(text="+",
                size_hint_x=None, width=dp(38), height=dp(38),
                md_bg_color=(1, 0.72, 0, 1), font_size="18sp",
                theme_text_color="Custom",
                text_color=(0, 0.19, 0.53, 1))
            def make_minus(s, inp):
                def fn(x):
                    v = int(inp.text or 0)
                    if v > 0: inp.text = str(v - 1)
                    self._passengers[s] = int(inp.text)
                return fn
            def make_plus(s, inp):
                def fn(x):
                    inp.text = str(int(inp.text or 0) + 1)
                    self._passengers[s] = int(inp.text)
                return fn
            def make_change(s, inp):
                def fn(instance, value):
                    try: self._passengers[s] = int(value or 0)
                    except ValueError: self._passengers[s] = 0
                return fn
            minus_btn.bind(on_release=make_minus(stop, ti))
            plus_btn.bind(on_release=make_plus(stop, ti))
            ti.bind(text=make_change(stop, ti))
            row.add_widget(lbl)
            row.add_widget(minus_btn)
            row.add_widget(ti)
            row.add_widget(plus_btn)
            container.add_widget(row)
            self._stop_inputs[stop] = ti

    def complete_trip(self):
        if sum(self._passengers.values()) == 0:
            self.show_dialog("Error",
                "Please add at least one passenger." if get_lang()=="en" else "Magdagdag ng kahit isang pasahero.")
            return
        app    = MDApp.get_running_app()
        result = log_multi_stop_trip(
            app.current_user["id"],
            self._trip_from, self._trip_to, self._passengers)
        self._trip_active = False
        self._passengers  = {}
        self.ids.stop_rows.clear_widgets()
        self.ids.start_trip_btn.disabled    = False
        self.ids.complete_trip_btn.disabled = True
        self.ids.from_spinner.disabled      = False
        self.ids.to_spinner.disabled        = False
        self.trip_summary  = ""
        self.trip_hint_txt = t("trip_hint")
        self.refresh_data()
        pax_lines = "\n".join(
            [f"  {s}: {n} × ₱{compute_fare(result['from'], s)[0]:.0f}"
             for s, n in result["passengers"].items() if n > 0])
        if get_lang() == "en":
            msg = (f"Route: {result['from']} → {result['to']}\n"
                   f"Distance: {result['distance']:.1f} km\n\n"
                   f"Passengers:\n{pax_lines}\n\n"
                   f"Total fare: ₱{result['total_fare']:.2f}\n"
                   f"Fuel cost: ₱{result['fuel_cost']:.2f}\n"
                   f"Net income: ₱{result['net']:.2f}")
            self.show_dialog("Trip Complete! 🎉", msg)
        else:
            msg = (f"Ruta: {result['from']} → {result['to']}\n"
                   f"Distansya: {result['distance']:.1f} km\n\n"
                   f"Mga pasahero:\n{pax_lines}\n\n"
                   f"Kabuuang pamasahe: ₱{result['total_fare']:.2f}\n"
                   f"Gastos sa gasolina: ₱{result['fuel_cost']:.2f}\n"
                   f"Netong kita: ₱{result['net']:.2f}")
            self.show_dialog("Tapos na ang Biyahe! 🎉", msg)

    def confirm_new_day(self):
        app   = MDApp.get_running_app()
        count = clear_today(app.current_user["id"])
        msg = (f"Today had {count} trip(s).\nThe records are saved in History.\nStarting fresh!"
               if get_lang()=="en" else
               f"Ngayon ay may {count} biyahe.\nNaka-save sa History.\nSimula ng bago!")
        d = MDDialog(
            title="New Day / Bagong Araw" ,
            text=msg,
            buttons=[
                MDFlatButton(text="Cancel" if get_lang()=="en" else "Kanselahin",
                    on_release=lambda x: d.dismiss()),
                MDRaisedButton(
                    text="New Day!" if get_lang()=="en" else "Bagong Araw!",
                    md_bg_color=(1, 0.72, 0, 1),
                    theme_text_color="Custom",
                    text_color=(0, 0.19, 0.53, 1),
                    on_release=lambda x: self._do_new_day(d))
            ])
        d.open()

    def _do_new_day(self, dialog):
        dialog.dismiss()
        # Data stays in DB — new day just resets the view
        # Since get_today_summary uses current date, tomorrow it auto-resets
        self.refresh_data()
        self.show_dialog(
            "New Day Started! 🌅" if get_lang()=="en" else "Bagong Araw! 🌅",
            "Your history is saved. Have a great day!" if get_lang()=="en"
            else "Naka-save ang kasaysayan mo. Mag-ingat sa biyahe!")

    def show_dialog(self, title, message):
        d = MDDialog(title=title, text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()

    def do_logout(self):
        MDApp.get_running_app().current_user = {}
        self.manager.current = "login"


class DriverHistoryScreen(Screen):
    history_title = StringProperty("")
    history_sub   = StringProperty("")

    def on_enter(self):
        self.refresh_lang()
        self.load_history()

    def refresh_lang(self):
        self.history_title = t("history_title")
        self.history_sub   = t("history_sub")

    def load_history(self):
        app     = MDApp.get_running_app()
        records = get_daily_history(app.current_user["id"])
        self.ids.history_list.clear_widgets()
        from kivymd.uix.card import MDCard
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivy.metrics import dp

        if not records:
            self.ids.history_list.add_widget(MDLabel(
                text="No history yet." if get_lang()=="en" else "Wala pang kasaysayan.",
                halign="center", theme_text_color="Secondary",
                size_hint_y=None, height="48dp"))
            return

        for r in records:
            card = MDCard(size_hint_y=None, height=dp(80),
                padding=dp(14), radius=[12], elevation=1,
                md_bg_color=(1, 1, 1, 1))
            outer = MDBoxLayout(orientation="horizontal")

            # Left — date + trips
            left = MDBoxLayout(orientation="vertical", size_hint_x=0.55)
            left.add_widget(MDLabel(
                text=r["trip_date"],
                font_style="Subtitle2", bold=True,
                theme_text_color="Custom",
                text_color=(0.01, 0.19, 0.53, 1),
                size_hint_y=None, height=dp(24)))
            left.add_widget(MDLabel(
                text=f"{r['trip_count']} {'trips' if get_lang()=='en' else 'biyahe'}",
                font_style="Caption",
                theme_text_color="Secondary"))

            # Right — income / fuel / net
            right = MDBoxLayout(orientation="vertical", size_hint_x=0.45)
            right.add_widget(MDLabel(
                text=f"₱{r['total_income']:.0f}  {'income' if get_lang()=='en' else 'kita'}",
                font_style="Caption", halign="right",
                theme_text_color="Custom",
                text_color=(1, 0.72, 0, 1)))
            right.add_widget(MDLabel(
                text=f"₱{r['total_fuel']:.0f}  {'fuel' if get_lang()=='en' else 'gasolina'}",
                font_style="Caption", halign="right",
                theme_text_color="Custom",
                text_color=(0.8, 0.2, 0.2, 1)))
            right.add_widget(MDLabel(
                text=f"₱{r['total_net']:.0f}  net",
                font_style="Caption", bold=True, halign="right",
                theme_text_color="Custom",
                text_color=(0.01, 0.19, 0.53, 1)))

            outer.add_widget(left)
            outer.add_widget(right)
            card.add_widget(outer)
            self.ids.history_list.add_widget(card)


class DriverTipsScreen(Screen):
    tips_title = StringProperty("")
    tips_sub   = StringProperty("")

    def on_enter(self):
        self.refresh_lang()
        self.load_tips()

    def refresh_lang(self):
        self.tips_title = t("tips_title")
        self.tips_sub   = t("tips_sub")

    def load_tips(self):
        app  = MDApp.get_running_app()
        tips = get_recommendations(app.current_user["id"])
        self.ids.tips_list.clear_widgets()
        from kivymd.uix.card import MDCard
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivy.metrics import dp
        colors = {
            "peak":    (0.93, 0.97, 1.0, 1),
            "low":     (1.0, 0.97, 0.88, 1),
            "demand":  (0.93, 0.97, 1.0, 1),
            "fuel":    (1.0, 0.93, 0.93, 1),
            "warning": (1.0, 0.93, 0.93, 1),
        }
        for tip in tips:
            card = MDCard(size_hint_y=None, height=dp(80), padding=dp(14),
                md_bg_color=colors.get(tip["type"], (0.95, 0.95, 0.95, 1)),
                radius=[12], elevation=1)
            box = MDBoxLayout(orientation="vertical", spacing=dp(4))
            box.add_widget(MDLabel(text=tip["title"], font_style="Subtitle2",
                bold=True, theme_text_color="Custom",
                text_color=(0.01, 0.19, 0.53, 1),
                size_hint_y=None, height=dp(24)))
            box.add_widget(MDLabel(text=tip["body"], font_style="Caption",
                theme_text_color="Secondary"))
            card.add_widget(box)
            self.ids.tips_list.add_widget(card)


class SakayKoApp(MDApp):
    current_user = {}

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        create_tables()
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(RegisterScreen(name="register"))
        sm.add_widget(DriverHomeScreen(name="driver_home"))
        sm.add_widget(DriverTipsScreen(name="driver_tips"))
        sm.add_widget(DriverHistoryScreen(name="driver_history"))
        sm.add_widget(PassengerHomeScreen(name="passenger_home"))
        return sm

    def on_start(self):
        Clock.schedule_once(lambda dt: self.go_to_login(), 2)

    def go_to_login(self):
        self.root.current = "login"

if __name__ == "__main__":
    SakayKoApp().run()