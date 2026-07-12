from core.common.error_manager import AppDebugger

class ReadyCodeFlow:
    """מחלקה עצמאית שמנהלת את סדר הפעולות והלוגיקה של מסך קוד מוכן"""

    def __init__(self, screen_manager):
        self.screen_manager = screen_manager

    def start(self):
        AppDebugger.log("ReadyCodeFlow: מתחיל סדר פעולות עבור מסך קוד מוכן...")
        # כאן תבוא הלוגיקה הבאה של מסך הקוד המוכן כשתבנה אותו
        self.screen_manager.switch_to("ready_code")