
def queue(topic, cls='flow', topicspace='tg'):
    """
    Create a queue identifier in CLASS:TOPICSPACE:TOPIC format.

    Args:
        topic: The logical queue name (e.g. 'config', 'librarian')
        cls: Queue class determining operational characteristics:
             - 'flow' = persistent processing pipeline queue
             - 'request' = non-persistent, short TTL request queue
             - 'response' = non-persistent, short TTL response queue
             - 'state' = persistent, last-value state broadcast
        topicspace: Deployment isolation prefix (default: 'tg')

    Returns:
        Queue identifier string: cls:topicspace:topic

    Examples:
        queue('text-completion-request')
            # flow:tg:text-completion-request
        queue('config', cls='request')
            # request:tg:config
        queue('config', cls='state')
            # state:tg:config
    """
    return f"{cls}:{topicspace}:{topic}"
