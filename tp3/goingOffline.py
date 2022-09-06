from message import Message, MessageType


class GoingOfflineMessage(Message):
    def __init__(self, sender_id,tracker):
        super().__init__(sender_id,tracker = tracker)
        self.type = MessageType.GOINGOFFLINE
