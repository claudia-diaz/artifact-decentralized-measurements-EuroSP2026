import math

from Message_cd import Message
from numpy.random import exponential
from constants import K
import random

global_bin = 0

class Client:

    def __init__(self, simulation, client_id):
        self.simulation = simulation  # simulation object
        self.env = simulation.env
        self.config = simulation.config
        self.id = client_id
        self.msg_serial = 0  # message index counter
        self.online_status = True
        self.current_volume = K.VOLUME_BASELINE
        self.env.process(self.toggle_online_status())
        self.env.process(self.toggle_traffic_volume())
        self.env.process(self.send_messages())

    def toggle_online_status(self):

        # initialize by setting online status proportionally to % of time online
        percent_online = self.config.client_online_duration/(
            self.config.client_online_duration + self.config.client_offline_duration)
        if random.random() < percent_online:  # client starts online
            self.online_status = True
            next_toggle = exponential(self.config.client_online_duration)
            if self.config.printing:
                print("client", self.id, "starts online ; for duration:", round(next_toggle, 4))
        else:  # client starts offline
            self.online_status = False
            next_toggle = exponential(self.config.client_offline_duration)
            if self.config.printing:
                print("client", self.id, "starts offline ; for duration:", round(next_toggle, 4))

        while True:
            yield self.env.timeout(next_toggle)
            if self.online_status:  # client is online, goes offline
                self.online_status = False
                next_toggle = exponential(self.config.client_offline_duration)
                if self.config.printing:
                    print("client", self.id, "going offline for duration ", next_toggle)
            else:  # client if offline, goes online
                self.online_status = True
                next_toggle = exponential(self.config.client_online_duration)
                if self.config.printing:
                    print("client", self.id, "going online for duration ", next_toggle)

    def toggle_traffic_volume(self):

        # initialize setting volume proportionally to % of time in baseline volume
        percent_baseline = self.config.client_baseline_volume_duration/(
                self.config.client_baseline_volume_duration + self.config.client_high_volume_duration)
        if random.random() < percent_baseline:  # starts in baseline traffic
            self.current_volume = K.VOLUME_BASELINE  # start proportionally to % of baseline traffic
            next_toggle = exponential(self.config.client_baseline_volume_duration)
            if self.config.printing:
                print("client", self.id, "starts in baseline volume ; for duration:", round(next_toggle, 4))
        else:  # starts in high traffic
            self.current_volume = K.VOLUME_HIGH
            next_toggle = exponential(self.config.client_high_volume_duration)
            if self.config.printing:
                print("client", self.id, "starts in high volume ; for duration:", round(next_toggle, 4))

        while True:
            yield self.env.timeout(next_toggle)
            if self.current_volume == K.VOLUME_BASELINE:  # client is in baseline, changes to high volume
                self.current_volume = K.VOLUME_HIGH
                next_toggle = exponential(self.config.client_high_volume_duration)
                if self.config.printing:
                    print("client", self.id, "going high volume for", round(next_toggle,4), "; message index: ", self.msg_serial)
            else: # client is in high, goes to baseline
                self.current_volume = K.VOLUME_BASELINE
                next_toggle = exponential(self.config.client_baseline_volume_duration)
                if self.config.printing:
                    print("client", self.id, "going to baseline volume for", round(next_toggle,4), "; message index: ", self.msg_serial)

    def create_message(self, msg_type):

        route = self.simulation.network.get_acked_route(msg_type)
        delays = self.simulation.network.get_delays_route()
        time_creation = self.env.now

        bin_nr = round(min(time_creation // self.config.bin_width, self.config.total_bins-1))  # in case it went overtime for the very last messages
        msg = Message(self.msg_serial, msg_type, self, route, delays, time_creation, bin_nr)
        self.msg_serial += 1

        global global_bin
        if bin_nr > global_bin:
            print("Finished bin", bin_nr, " / ", self.config.total_bins)
            global_bin = bin_nr

        return msg

    def send_messages(self):

        while not self.check_end_sim():

            if self.current_volume == K.VOLUME_BASELINE:
                interval_msg = self.config.send_interval_baseline_traffic
            else:
                interval_msg = self.config.send_interval_high_traffic

            yield self.env.timeout(exponential(interval_msg))

            if not self.online_status:
                continue  # do not create message if client offline, try again after another random interval_msg

            # if client is online, create a message
            if random.random() < self.config.lottery:
                msg_type = K.MSG_MEASUREMENT
            else:  # message can be real or dummy
                if random.random() < self.config.dummy_rate:
                    msg_type = K.MSG_DUMMY
                else:
                    msg_type = K.MSG_REAL
            msg = self.create_message(msg_type)
            self.simulation.network.route_message(msg)

        yield self.env.timeout(self.config.grace_period_end_sim)
        self.simulation.end_event.succeed()  # end simulation if time has expired

    def check_end_sim(self):  # check to end simulation logic

        #if self.simulation.network.num_messages > 500 * 10**3:
        if self.env.now > self.config.sim_duration:
            if self.config.printing:
                print("Simulation duration limit reached: ", self.env.now, " by client: ", self.id)
            return True
        else:
            return False
