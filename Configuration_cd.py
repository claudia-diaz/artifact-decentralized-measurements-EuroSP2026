import time
import math
from scipy.stats import beta
from constants import K


class Configuration:
    def __init__(self, adversaries, targets, prob_drop_attack):
        # set network and mix parameters
        self.num_layers = 3
        self.width_layers = 80
        self.num_gateways = 80  # MINIMUM 2 !! (gateway 0 is used for the broadcast address, not for clients)
        self.total_nodes = self.num_gateways + self.num_layers * self.width_layers
        self.num_adversaries = adversaries  # nr of malicious gateways / nodes per layer (vector)
        self.num_targets = targets  # nr of targeted nodes per layer (vector)
        self.prob_drop_attack = prob_drop_attack  # probability with which a malicious node will drop a message to/from a target

        self.delay_mix_seconds = 0.050   # 50ms per mix on average
        self.delay_mix = self.delay_mix_seconds * K.TPS  # delay expressed in ticks

        # set simulation timing parameters
        self.sim_duration = 1 * 60 * 60 * K.TPS  # duration of the simulation (in ticks)
        self.grace_period_end_sim = 10 * self.num_layers * self.delay_mix  # 10x avg e2e full routes
        self.total_bins = 1  # nr periods that sim_duration is divided in, so that, eg, 1 bin = 5 min)
        self.bin_width = self.sim_duration / self.total_bins
        self.bin_width_sec = round(self.bin_width/K.TPS)  # width of a bin in seconds
        self.start_time = time.time()  # timestamp start of simulation

        # set printing and logging flags
        self.printing = False
        self.logging = True
        self.log_dir = 'Logs/'

        # lottery and performance parameters
        self.lottery = 1.0  # 0.01  # 1.0  #0.01  # fraction of messages that are measurement messages
        self.min_perf = 0.99  # if perf < min_perf for median of the links in/out a node, it is marked as offine/faulty
        self.beta_sim = math.sqrt(self.width_layers * (self.width_layers-1)) - self.width_layers + 1

        # client traffic parameters designed to generate high-variance input traffic load to stress-test the setting
        self.num_clients = 1  # 8000 #200
        self.dummy_rate = 0.5  # fraction of non-measurement messages that are dummy (loop) messages
        self.client_online_duration = 365 * 60 * 60 * K.TPS  # 10 * 60 * K.TPS average time online (10 min)
        self.client_offline_duration = 0  # 1 * 60 * K.TPS  # average time offline (1 min)
        self.send_interval_baseline_traffic = (1/560) * K.TPS  # (1/50) * K.TPS  # baseline volume per client (inter-packet time)
        self.send_interval_high_traffic = self.send_interval_baseline_traffic  # (1/500) * K.TPS  # high traffic volume (inter-packet time)
        self.client_baseline_volume_duration = 365 * 60 * 60 * K.TPS  # 9 * 60 * K.TPS  # duration of baseline traffic load period
        self.client_high_volume_duration = 0  # 1 * 60 * K.TPS  # duration of high traffic load period

        # initialize node parameters for capacity, on/off periods and drop rates
        #self.list_capacity_nodes = []
        #capacities_gateways = [40000] * self.num_gateways  # gateways assumed to have 2x higher capacity than nodes
        #capacities_nodes = [20000] * (self.total_nodes - self.num_gateways)  # default: 5k msg/s per CPU core, x4 cores
        #self.list_capacity_nodes.extend(capacities_gateways)  # default is 5000 msg/s per CPU core and x4 cores
        #self.list_capacity_nodes.extend(capacities_nodes)  # default is 5000 msg/s per CPU core and x4 cores

        self.list_capacity_nodes = [20000.0] * self.total_nodes
        self.list_online_periods = [365 * 24 * 60 * 60 * K.TPS] * self.total_nodes  # mean uptime
        self.list_offline_periods = [0.0] * self.total_nodes  # mean down time duration
        self.list_droprates_in = [0.0] * self.total_nodes  # random independent drops (while online)
        self.list_droprates_out = [0.0] * self.total_nodes  # random independent drops (while online)

        # initialize node parameters corruption
        self.list_corrupt = [0] * self.total_nodes  # 0 if honest, 1 if corrupt
        self.list_target = [0] * self.total_nodes  # 0 if not a target of attack, 1 if target

        self.set_adversaries_and_targets()
        self.set_weird_behaviour_nodes()

    def set_weird_behaviour_nodes(self):

        # set (overwrite node variable values): abnormally low capacity, low uptime, high drop rates
        # one node in each layer has the weird behaviour
        nr_reliable_layer = 40  # half of the layer -- this needs update if nr nodes/gateways changes !!!!
        nr_unreliable_layer = 16
        online = 1.5 * 60 * 60 * K.TPS
        offline = 10 * 60 * K.TPS
        baserate = K.TPS / (self.send_interval_baseline_traffic * self.width_layers)
        low_capacities = [baserate, baserate/2, baserate/4, baserate/8]
        droprates_in = [0.01, 0.2]
        droprates_out = [0.01, 0.2]

        for layer in range(self.num_layers + 1):
            if layer == 0:
                node_index = nr_reliable_layer
            else:
                node_index = self.num_gateways + (layer-1) * self.width_layers + nr_reliable_layer

            for i in range(nr_unreliable_layer):
                self.list_online_periods[node_index] = online
                self.list_offline_periods[node_index] = offline
                node_index += 1
            for capacity in low_capacities:
                self.list_capacity_nodes[node_index] = capacity
                node_index += 1
            for droprate in droprates_in:
                self.list_droprates_in[node_index] = droprate
                node_index += 1
            for droprate in droprates_out:
                self.list_droprates_out[node_index] = droprate
                node_index += 1


    def set_adversaries_and_targets(self):

        for layer in range(self.num_layers + 1):
            if layer == 0:
                start_index = 1  # set target gateways excluding gateway zero (blockchain broadcast)
            else:
                start_index = self.num_gateways + (layer - 1) * self.width_layers

            # set targets as first indexes in layer
            for target_id in range(start_index, start_index + self.num_targets[layer]):
                self.list_target[target_id] = 1
                self.list_online_periods[target_id] = 365 * 24 * 60 * 60 * K.TPS  # target nodes huge uptime
                self.list_offline_periods[target_id] = K.TPS/10000  # target nodes never offline
                self.list_droprates_in[target_id] = 0.0  # target nodes have no random incoming drops
                self.list_droprates_out[target_id] = 0.0  # target nodes have no random outgoing drops

            # set malicious nodes as following indexes
            for i in range(self.num_adversaries[layer]):
                node_id = start_index + self.num_targets[layer] + i
                self.set_node_corrupt(node_id)

    def set_node_corrupt(self, node_id):

        self.list_corrupt[node_id] = 1
        self.list_online_periods[node_id] = 365 * 24 * 60 * 60 * K.TPS  # adversarial nodes huge uptime
        self.list_offline_periods[node_id] = K.TPS/10000  # adversarial nodes never offline
        #self.list_capacity_nodes[node_id] = 5000  # adversarial nodes have more capacity (5x)
        self.list_droprates_in[node_id] = 0.0  # adversarial nodes have no random incoming drops
        self.list_droprates_out[node_id] = 0.0  # adversarial nodes have no random outgoing drops

    def get_index_node(self, node_id):
        if node_id < self.num_gateways:
            index = node_id  # the index coincides with gateway id
        else:
            layer = (node_id - self.num_gateways) // self.width_layers
            index = node_id - self.num_gateways - layer * self.width_layers
        return index

    # compute the max error given the nr of samples, the estimated prob, and confidence level K.Z
    def compute_max_error_bin(self, prob_list, count_list):

        max_error = [1.0] * self.total_bins
        for bin_nr in range(self.total_bins):
            if count_list[bin_nr] > 0 and 0 < prob_list[bin_nr] < 1:
                p = prob_list[bin_nr]
                max_error[bin_nr] = min(1.0, K.Z * math.sqrt(p * (1 - p) / count_list[bin_nr]))
            else:
                max_error[bin_nr] = 1 / (count_list[bin_nr] + 2)

        return max_error

    # returns list1[i]/list2[i]
    def compute_fraction_lists(self, list1, list2):
        size = len(list2)
        fraction = [0] * size
        for bin_nr in range(size):
            if list2[bin_nr] > 0:
                fraction[bin_nr] = list1[bin_nr] / list2[bin_nr]
        return fraction

    # returns:  1 - list1[i]/list2[i]
    def compute_one_minus_fraction_lists(self, list1, list2):
        size = len(list2)
        fraction = [0] * size
        for bin_nr in range(size):
            if list2[bin_nr] > 0:
                fraction[bin_nr] = 1.0 - list1[bin_nr] / list2[bin_nr]
        return fraction




