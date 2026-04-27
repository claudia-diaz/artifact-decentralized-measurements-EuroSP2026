from constants import K

class Message:
    def __init__(self, serial, type, sender, route, delays, time_created, bin_nr):
        self.id = "%d_%d" % (sender.id, serial)
        self.type = type  # Real(0), Measurement(1), Dummy(2)
        self.sender = sender  # sender object
        self.hop = 0  # index of current routing hop
        self.route = route  # e.g. [g1, mix1, mix2, mix3, g1, mix4, mix5, mix6, g2, Broadcast]
        self.delays = delays  # list of delays at each hop
        self.trace_links = []  # links were the message has been reported []
        self.dropped_by = K.NOBODY  # -1 if not dropped, mix.id if dropped
        self.dropped_at_hop = K.NOBODY  # index of node in route that dropped the message, -1 if not dropped
        self.time_created = time_created
        self.bin_nr = bin_nr
        self.time_received = -1
        self.time_dropped = -1

