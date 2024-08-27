
def topic(topic, kind='persistent', tenant='tg', namespace='flow'):
    return f"{kind}://{tenant}/{namespace}/{topic}"

