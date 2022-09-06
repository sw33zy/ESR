from message import Message, MessageType
from tracker import Tracker

class DataMessage(Message):
    def __init__(self, sender_id,tracker, rtppacket):
        super().__init__(sender_id, tracker=tracker)
        self.type = MessageType.DATA
        self.rtppacket = rtppacket


    def get_rtppacket(self):
        return self.rtppacket

    def set_rtppacket(self, rtppacket):
        self.rtppacket = rtppacket




