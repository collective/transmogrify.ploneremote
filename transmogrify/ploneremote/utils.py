
def replaceMicrosoftChars(text):
    text = text.replace(u"\u2019", u"'")
    text = text.replace(u"\u201c", u'"')
    text = text.replace(u"\u201d", u'"')
    return text
