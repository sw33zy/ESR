from message import Message, MessageType


class SPeersMessage(Message):
    def __init__(self, sender_id, neighbours):
        super().__init__(sender_id)
        self.type = MessageType.SPEERS
        self.neighbours = neighbours


    def get_neighbours(self):
        return self.neighbours

