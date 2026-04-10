
def queue(topic, cls='flow', topicspace='tg'):
    """
    Create a queue identifier in CLASS:TOPICSPACE:TOPIC format.

    Args:
        topic: The logical queue name (e.g. 'config', 'librarian')
        cls: Queue class determining operational characteristics:
             - 'flow' = persistent shared work queue (competing consumers)
             - 'request' = non-persistent RPC request queue (shared)
             - 'response' = non-persistent RPC response queue (per-subscriber)
             - 'notify' = ephemeral broadcast (per-subscriber, auto-delete)
        topicspace: Deployment isolation prefix (default: 'tg')

    Returns:
        Queue identifier string: cls:topicspace:topic

    Examples:
        queue('text-completion-request')
            # flow:tg:text-completion-request
        queue('config', cls='request')
            # request:tg:config
        queue('config', cls='notify')
            # notify:tg:config
    """
    return f"{cls}:{topicspace}:{topic}"
