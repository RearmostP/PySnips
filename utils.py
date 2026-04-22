from bidi.algorithm import get_display


# תיקון ה rlt של העברית
def rtl(text):
    return get_display(text)


# ממיר rgba ל rgb
def rgb(r, g, b, a=255):
    values = []
    for v in (r, g, b, a):
        v = max(0, min(255, v))
        values.append(v / 255)
    return tuple(values)
