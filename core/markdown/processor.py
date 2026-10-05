import markdown


def to_html(text, style='default'):
    html = markdown.markdown(text, extensions=['fenced_code', 'codehilite', 'tables', 'sane_lists'],
                             extension_configs={'codehilite': {'guess_lang': False, 'noclasses': True,
                                                               'nobackground': True, 'pygments_style': style}})
    return html.replace('<pre', '<pre dir="ltr"')
