from datetime import time

import datetime
from enum import Enum



class MessageType(Enum):
    ACK = 0
    DATA = 1
    MESSAGE = 2
    PING = 3
    SPEERS = 4
    GOINGOFFLINE = 5





def generate_timestamp():
    ct = datetime.datetime.now()
    ts = ct.timestamp()
    return ts


def convert_timestamp(ts):
    ct = datetime.datetime.fromtimestamp(ts)
    return ct


class Message:
    def __init__(self, sender_id, timestamp=None, tracker=None):
        self.type = MessageType.MESSAGE
        self.sender_id = sender_id
        self.tracker = tracker
        if timestamp is None:
            self.timestamp = generate_timestamp()
        # getter method

    def get_message(self):
        return self.message

    def get_timestamp(self):
        return self.timestamp

    def get_sender_id(self):
        return self.sender_id

    def get_type(self):
        return self.type

    def get_tracker(self):
        return self.tracker

    def set_tracker(self,tracker):
        self.tracker = tracker
