class SubscriptionAlreadyExists(Exception):
    """Exception raised when a user already has a subscription to a stream."""
    pass

class MessageBrokerNotAvailable(Exception):
    """Raised when the broker is not online"""
    pass
