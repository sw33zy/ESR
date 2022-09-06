from message import Message, MessageType


class ACKMessage(Message):
    def __init__(self, sender_id):
        super().__init__(sender_id)
        self.type = MessageType.ACK
