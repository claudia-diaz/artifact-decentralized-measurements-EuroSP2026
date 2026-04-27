import random
from constants import K
from numpy.random import exponential
from Count_cd import Counters
import math


class Mix:

    def __init__(self, simulation, mix_type, mix_id, layer):

        self.simulation = simulation
        self.config = simulation.config
        self.env = simulation.env
        self.log = simulation.log

        # node identifier, type, and position
        self.id = mix_id  # node id, serial nr, first numbers correspond to gateways
        self.type = mix_type  # MIX or GATEWAY
        self.layer = layer  # layer where node is placed

        # node initial state: online and empty
        self.pool = []  # internal message pool of the mix
        self.online_status = True
        self.current_bin = 0  # initial counter for uptime
        self.bin_fillup = 0.0  # counter for uptime counting

        # links of the node, set at network creation by Network class
        self.client_links = []  # only for gateways
        self.incoming_links = []  # list of in links
        self.outgoing_links = []  # list of out links
        self.perf_dict = {}  # dictionary with info on links in and out of the node

        # parameters relevant to node dropping behavior
        self.droprate_in = self.config.list_droprates_in[self.id]  # rate random dropping of incoming messages
        self.droprate_out = self.config.list_droprates_out[self.id]  # rate random dropping of outgoing messages
        self.online_mean_period = self.config.list_online_periods[self.id]
        self.offline_mean_period = self.config.list_offline_periods[self.id]
        self.capacity = self.config.list_capacity_nodes[self.id]  # node max capacity in messages per __second__
        self.cap100ms = math.floor(self.capacity/10)  # capacity (nr messages) per 100 ms

        # attack parameters
        self.corrupt = self.config.list_corrupt[self.id]  # corrupt mix (1) or honest (0)
        self.target = self.config.list_target[self.id]  # target of attack (1) or not a target (0)

        self.counters = Counters(self.config)
        self.env.process(self.toggle_online_offline())

    def receive_msg(self, msg):

        yield self.env.timeout(K.TRANSMISSION_TIME)

        if len(msg.trace_links) == 0:  # client --> gateway (1st hop)
            self.set_counts_gateway_receive_from_client(msg)
        else:  # node receives the message from another node (not client)
            self.set_counts_node_receive(msg)

        if self.decide_drop_message(msg, K.INBOUND):  # msg dropped on in-link
            # set message drop parameters and add to message log
            msg.dropped_by = self.id
            msg.dropped_at_hop = msg.hop
            msg.trace_links.append(-1)
            msg.time_dropped = self.env.now
            #self.simulation.network.list_messages.append(msg)
            self.simulation.network.num_messages += 1
            if msg.type == K.MSG_MEASUREMENT:
                self.simulation.network.num_msm_messages += 1
            if self.config.printing:
                self.log.print_mix_event('Drop IN link', self.id, msg.id)
            # set node and link counts
            if len(msg.trace_links) == 1:  # drop in link client --> gateway (1st hop)
                self.set_drop_counts_gateway_receive_from_client(msg)
            else:  # drop in link between nodes
                self.set_drop_counts_node_receive(msg)

        else:  # message is added to the pool
            self.pool.append(msg)
            self.counters.time_sequence_processed_in.append(self.env.now)
            msg.trace_links.append(self.id)  # message received by node and added to merkle tree
            if self.config.printing:
                self.log.print_mix_event('Arrive', self.id, msg.id)
            self.env.process(self.send_msg(msg))

    def send_msg(self, msg):

        yield self.env.timeout(msg.delays[msg.hop])  # apply delay at this hop

        self.pool.remove(msg)  # message removed from the pool
        msg.hop += 1  # message advances one hop
        if msg.hop < len(msg.route):  # if message goes to another hop
            self.set_counts_node_send(msg)

        if self.decide_drop_message(msg, K.OUTBOUND):  # random drop out or mix currently offline
            msg.trace_links.append(-1)
            msg.dropped_by = self.id
            msg.dropped_at_hop = msg.hop
            msg.time_dropped = self.env.now
            #self.simulation.network.list_messages.append(msg)
            self.simulation.network.num_messages += 1
            if msg.type == K.MSG_MEASUREMENT:
                self.simulation.network.num_msm_messages += 1
            if self.config.printing:
                self.log.print_mix_event('Drop pool / OUT link', self.id, msg.id)
                self.log.print_message(msg)
            # set node and link drop counts
            self.set_drop_counts_node_send(msg)

        else:  # message not dropped on outgoing link
            if self.config.printing:
                self.log.print_mix_event('Message leave', self.id, msg.id)
            if msg.hop < len(msg.route):  # message goes to another node
                next_node = self.simulation.network.list_nodes[msg.route[msg.hop]]
                self.env.process(next_node.receive_msg(msg))
            else:  # message at the end of the route
                msg.time_received = self.env.now
                #self.simulation.network.list_messages.append(msg) # message finished route
                self.simulation.network.num_messages += 1
                if msg.type == K.MSG_MEASUREMENT:
                    self.simulation.network.num_msm_messages += 1
                if self.config.printing:
                    self.log.print_mix_event('Message reaches end of route', self.id, msg.id)
                    self.log.print_message(msg)
                # set node counts for the message delivered
                self.set_counts_node_messages_delivered(msg)

    def decide_drop_message(self, msg, direction):

        if not self.online_status:  # node currently offline
            return True  # drop message

        if direction == K.INBOUND:
            if random.random() < self.droprate_in:  # random drop while online (bernoulli process)
                return True  # drop message
        else:
            if random.random() < self.droprate_out:  # random drop while online (bernoulli process)
                return True  # drop message

        # remove INBOUND condition if messages are also dropped in outbound links when node is congested
        # I assume sending is prioritized and node only drops incoming messages when at capacity
        if direction == K.INBOUND and self.capacity_full():
            return True  # drop the incoming message due to full capacity

        # incoming messages
        if self.corrupt and direction == K.INBOUND:
            if msg.hop == 0:  # malicious node is a gateway receiving msg from client
                return False  # do not drop messages coming from clients
            pred_id = msg.route[msg.hop-1]
            if self.simulation.network.list_nodes[pred_id].target and random.random() < self.config.prob_drop_attack:
                self.counters.attack_drop_in_all[msg.bin_nr] += 1
                if msg.type == K.MSG_MEASUREMENT:
                    self.counters.attack_drop_in_msm[msg.bin_nr] += 1
                return True  # drop incoming messages coming from target nodes
            else:
                return False  # do not drop messages coming from non-targets

        # outgoing messages
        elif self.corrupt and direction == K.OUTBOUND:
            if msg.hop == len(msg.route):  # malicious node is the end of the route
                return False  # do not drop messages going out to clients / blockchain / end recipients
            suc_id = msg.route[msg.hop]
            # message destined to a target node
            if self.simulation.network.list_nodes[suc_id].target and random.random() < self.config.prob_drop_attack:
                self.counters.attack_drop_out_all[msg.bin_nr] += 1
                if msg.type == K.MSG_MEASUREMENT:
                    self.counters.attack_drop_out_msm[msg.bin_nr] += 1
                return True  # drop messages going to a target
            else:
                return False  # do not drop messages going to non-targets or if random drop for target is negative

        return False  # message is not dropped and proceeds to next step

    def capacity_full(self):

        if len(self.counters.time_sequence_processed_in) < self.cap100ms+1:
            return False  # start of operations, mix did not even process max100ms messages yet

        ts_100ms_ago = self.env.now - 0.1 * K.TPS  # timestamp in the env time of 100ms earlier in the simulation
        ts0 = self.counters.time_sequence_processed_in[-self.cap100ms-1]  # timestamp of "message received" 100 msgs ago
        # trim the list to avoid consuming tons of memory
        self.counters.time_sequence_processed_in = self.counters.time_sequence_processed_in[-self.cap100ms-1:]

        if ts0 < ts_100ms_ago:  # ts of msg -100 is older than 100ms
            return False  # mix processed fewer than max100ms messages in the last 100ms, can process this one too
        else:  # mix processed more than max100ms messages in the last 100ms and it is saturated, this msg is dropped
            return True

    def toggle_online_offline(self):

        next_toggle = exponential(self.online_mean_period)  # starts online
        self.update_count_online(next_toggle)
        if self.config.printing:
            print('mix {} online until {}'.format(self.id, next_toggle))

        while True:
            yield self.env.timeout(next_toggle)
            if self.online_status:  # mix going offline
                self.online_status = False
                next_toggle = exponential(self.offline_mean_period)  # amount of time it will stay offline
                self.update_count_offline(next_toggle)
                if self.config.printing:
                    print('mix {} offline until {}'.format(self.id, next_toggle))
            else:
                self.online_status = True  # mix coming online
                next_toggle = exponential(self.online_mean_period)
                self.update_count_online(next_toggle)
                if self.config.printing:
                    print('mix {} online until {}'.format(self.id, next_toggle))

    def update_count_online(self, next_toggle):

        new_total = self.bin_fillup + next_toggle
        bin_span = new_total // self.config.bin_width
        last_bin = math.floor(min(self.current_bin + bin_span, self.config.total_bins))
        remainder = new_total % self.config.bin_width

        # add next_toggle to the appropriate uptime counters
        if self.current_bin == last_bin:  # current bin not yet full
            self.counters.uptime[self.current_bin] += next_toggle
            self.bin_fillup = remainder
        else:
            self.counters.uptime[self.current_bin] += self.config.bin_width - self.bin_fillup
            for bin_nr in range(self.current_bin + 1, last_bin):
                self.counters.uptime[bin_nr] = self.config.bin_width
            if last_bin < self.config.total_bins:  # not yet settled for the full time
                self.counters.uptime[last_bin] = remainder
                # update pointers to current status
                self.current_bin = last_bin
                self.bin_fillup = remainder
            else:
                self.current_bin = last_bin-1
                self.bin_fillup = self.config.bin_width

    def update_count_offline(self, next_toggle):

        new_total = self.bin_fillup + next_toggle
        bin_span = new_total // self.config.bin_width
        last_bin = math.floor(min(self.current_bin + bin_span, self.config.total_bins))
        remainder = new_total % self.config.bin_width
        # update pointers to current status
        if last_bin < self.config.total_bins:  # not yet settled for the full time
            # update pointers to current status
            self.current_bin = last_bin
            self.bin_fillup = remainder
        else:
            self.current_bin = last_bin-1
            self.bin_fillup = self.config.bin_width  # the whole set of bins is fully populated

    def set_counts_gateway_receive_from_client(self, msg):

        #self.counters.time_sequence_total_in_client.append(self.env.now)
        self.counters.in_client_all[msg.bin_nr] += 1
        link = self.client_links[0]  # only one client link for gateways (aggregating ALL clients)
        link.total_samples_all[msg.bin_nr] += 1

        if msg.type == K.MSG_MEASUREMENT:
            self.counters.in_client_msm[msg.bin_nr] += 1
            link.total_samples_msm[msg.bin_nr] += 1

    def set_drop_counts_gateway_receive_from_client(self, msg):

        #self.counters.time_sequence_true_drop_in_client.append(self.env.now)
        self.counters.true_drop_in_client_all[msg.bin_nr] += 1
        link = self.client_links[0]  # only one client link for gateways (aggregating ALL clients)
        link.dropped_samples_all[msg.bin_nr] += 1

        if msg.type == K.MSG_MEASUREMENT:
            self.counters.true_drop_in_client_msm[msg.bin_nr] += 1
            link.dropped_samples_msm[msg.bin_nr] += 1

    def set_counts_node_receive(self, msg):

        # set received counts for the node
        #self.counters.time_sequence_total_in.append(self.env.now)
        self.counters.in_all[msg.bin_nr] += 1
        if msg.type == K.MSG_MEASUREMENT:
            self.counters.in_msm[msg.bin_nr] += 1

    def set_drop_counts_node_receive(self, msg):

        # set drop counts for the node
        #self.counters.time_sequence_true_drop_in.append(self.env.now)
        self.counters.true_drop_in_all[msg.bin_nr] += 1
        # add drop counts to the link
        index_pred = self.config.get_index_node(msg.route[msg.hop-1])
        link = self.incoming_links[index_pred]
        link.dropped_samples_all[msg.bin_nr] += 1

        if msg.type == K.MSG_MEASUREMENT:
            self.counters.true_drop_in_msm[msg.bin_nr] += 1
            link.dropped_samples_msm[msg.bin_nr] += 1

    def set_counts_node_send(self, msg):

        # set received counts for the node
        #self.counters.time_sequence_total_out.append(self.env.now)
        self.counters.out_all[msg.bin_nr] += 1
        # add counts to the link
        index_suc = self.config.get_index_node(msg.route[msg.hop])
        link = self.outgoing_links[index_suc]
        link.total_samples_all[msg.bin_nr] += 1

        if msg.type == K.MSG_MEASUREMENT:
            self.counters.out_msm[msg.bin_nr] += 1
            link.total_samples_msm[msg.bin_nr] += 1

    def set_drop_counts_node_send(self, msg):

        # set drop counts for the node
        #self.counters.time_sequence_true_drop_out.append(self.env.now)
        self.counters.true_drop_out_all[msg.bin_nr] += 1
        if msg.type == K.MSG_MEASUREMENT:
            self.counters.true_drop_out_msm[msg.bin_nr] += 1

        if msg.hop < len(msg.route):
            index_suc = self.config.get_index_node(msg.route[msg.hop])
            link = self.outgoing_links[index_suc]
            link.dropped_samples_all[msg.bin_nr] += 1
            if msg.type == K.MSG_MEASUREMENT:
                link.dropped_samples_msm[msg.bin_nr] += 1

    def set_counts_node_messages_delivered(self, msg):

        # set received counts for the node
        #self.counters.time_sequence_delivered_all.append(self.env.now)
        self.counters.out_delivered_all[msg.bin_nr] += 1
        if msg.type == K.MSG_MEASUREMENT:
            #self.counters.time_sequence_delivered_msm.append(self.env.now)
            self.counters.out_delivered_msm[msg.bin_nr] += 1
