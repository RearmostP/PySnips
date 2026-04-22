from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

from utils import rtl, rgb

from screens.main_screen import MainScreen
from screens.ready_code_screen import ManagerReadyCodeScreen

Builder.load_file("screens/main_screen.kv")
Builder.load_file("screens/manager_ready_code_screen.kv")

class PySnipsApp(App):

    # תיקון ה rlt של העברית
    def rtl(self, text):
        return rtl(text)

    def rgb(self, r, g, b, a=255):
        return rgb(r, g, b, a=255)

    # צריך את זה כי kivy לא יודע לעבוד עם עברית
    font = 'assets/fonts/PlaypenSansHebrew.ttf'

    def build(self):

        app = ScreenManager()

        # מוסיפים מסכים
        app.add_widget(MainScreen(name="main"))
        app.add_widget(ManagerReadyCodeScreen(name="manager_ready_code_screen"))

        return app

if __name__ == '__main__':
    PySnipsApp().run()