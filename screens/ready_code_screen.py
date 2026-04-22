from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.screenmanager import Screen


class ManagerReadyCodeScreen(Screen):
    sidebar_open = BooleanProperty(True)
    sidebar_width_open = NumericProperty(220)
    sidebar_width_closed = NumericProperty(68)

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open