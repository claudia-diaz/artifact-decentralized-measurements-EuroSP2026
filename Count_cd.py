
class Counters:
    def __init__(self, config):

        self.config = config
        bins = self.config.total_bins

        # variables that hold the node counts of message drops per bin

        self.in_all = [0] * bins  # total messages coming into this node
        self.in_msm = [0] * bins  # total measurement messages coming into this node
        self.out_all = [0] * bins  # total messages coming out of this node
        self.out_msm = [0] * bins  # total measurement messages coming out of this node

        self.in_client_all = [0] * bins  # total messages coming into this node from clients
        self.in_client_msm = [0] * bins  # total measurement messages coming into this node from clients
        self.out_delivered_all = [0] * bins  # nr of messages delivered to recipient per bin
        self.out_delivered_msm = [0] * bins  # measurement messages delivered to the blockchain

        self.true_drop_in_client_all = [0] * bins  # total client messages dropped by node
        self.true_drop_in_client_msm = [0] * bins  # nr of measurement messages dropped by self in incoming link
        self.true_drop_in_all = [0] * bins  # nr of messages ACTUALLY dropped by this mix in incoming links
        self.true_drop_in_msm = [0] * bins  # nr of measurement messages dropped by self in incoming link
        self.true_drop_out_all = [0] * bins  # nr of messages ACTUALLY dropped by this mix in outgoing links
        self.true_drop_out_msm = [0] * bins  # nr of measurement messages dropped dropped by self in outgoing link

        self.obs_drop_in_client_all = [0] * bins  # total client messages dropped by node
        self.obs_drop_in_client_msm = [0] * bins  # total client measurement messages dropped by node
        self.obs_drop_in_all = [0] * bins  # values set in the evaluation (sum of link drops)
        self.obs_drop_in_msm = [0] * bins  # values set in the evaluation (sum of link drops)
        self.obs_drop_out_all = [0] * bins  # values set in the evaluation (sum of link drops)
        self.obs_drop_out_msm = [0] * bins  # values set in the evaluation (sum of link drops)

        self.filter_drop_in_all = [0] * bins  # post-processed (after assigning drops to mixes based on med)
        self.filter_drop_in_msm = [0] * bins  # post-processed (after assigning drops to mixes based on med)
        self.filter_drop_out_all = [0] * bins  # post-processed (after assigning drops to mixes based on med)
        self.filter_drop_out_msm = [0] * bins  # post-processed (after assigning drops to mixes based on med)

        self.attack_drop_in_all = [0] * bins  # drops done for the purpose of attack
        self.attack_drop_in_msm = [0] * bins  # drops done for the purpose of attack
        self.attack_drop_out_all = [0] * bins  # drops done for the purpose of attack
        self.attack_drop_out_msm = [0] * bins  # drops done for the purpose of attack

        self.no_attack_perf_in_all = [0] * bins  # drops done for the purpose of attack
        self.no_attack_perf_in_msm = [0] * bins  # drops done for the purpose of attack
        self.no_attack_perf_out_all = [0] * bins  # drops done for the purpose of attack
        self.no_attack_perf_out_msm = [0] * bins  # drops done for the purpose of attack

        # variables holding the statistics per bin of the node (functions of previous variables)

        self.frac_msm_in_client = [0] * bins  # in_client_msm/in_client_all
        self.frac_msm_out_delivered = [0] * bins  # out_delivered_msm/out_delivered_all

        self.true_perf_in_client_all = [0] * bins  # 1 - true_drop_in_client_all/in_client_all
        self.true_perf_in_client_msm = [0] * bins  # 1 - true_drop_in_client_msm/in_client_msm
        self.true_perf_in_all = [0] * bins  # 1 - true_drop_in_all/in_all
        self.true_perf_in_msm = [0] * bins  # 1 - true_drop_in_msm/in_msm
        self.true_perf_out_all = [0] * bins  # 1 - true_drop_out_all/out_all
        self.true_perf_out_msm = [0] * bins  # 1 - true_drop_out_msm/out_msm

        self.obs_perf_in_client_all = [0] * bins  # 1 - obs_drop_in_client_all/in_client_all
        self.obs_perf_in_client_msm = [0] * bins  # 1 - obs_drop_in_client_msm/in_client_msm
        self.obs_perf_in_all = [0] * bins  # 1 - obs_drop_in_all/in_all
        self.obs_perf_in_msm = [0] * bins  # 1 - obs_drop_in_msm/in_msm
        self.obs_perf_out_all = [0] * bins  # 1 - obs_drop_out_all/out_all
        self.obs_perf_out_msm = [0] * bins  # 1 - obs_drop_out_msm/out_msm

        self.filter_perf_in_all = [0.0] * bins  # 1 - filter_drop_in_all/in_all
        self.filter_perf_in_msm = [0.0] * bins  # 1 - filter_drop_in_all/in_msm
        self.filter_perf_out_all = [0.0] * bins  # 1 - filter_drop_out_all/out_all
        self.filter_perf_out_msm = [0.0] * bins  # 1 - filter_drop_out_all/out_msm

        # true percentage uptime (each element is between 0 and 1)
        self.uptime = [0.0] * bins  # raw numbers in ticks
        self.frac_uptime = [0.0] * bins

        # post-processed values after filtering
        self.marked_offline = [0] * bins  # True (1) when 1/2 of incoming links below threshold perf in bin (mix then takes blame for ALL incoming drops in bin)
        self.marked_faulty = [0] * bins  # True (1) when 1/2 of outgoing links below threshold perf in bin (mix then takes blame for ALL outgoing drops in bin)
        self.anomaly_in = []  # set of predecessors with whom the link has an anomaly (inexplicable low performance)
        self.anomaly_out = []  # set of successors with whom the link has an anomaly (inexplicable low performance)

        self.true_perf_all = 0
        self.true_perf_msm = 0
        self.filter_perf_all = 0
        self.filter_perf_msm = 0
        self.no_attack_perf_all = 0
        self.no_attack_perf_msm = 0
        self.obs_perf_all = 0
        self.obs_perf_msm = 0

        # timing sequences of message events and actual percentage of time that the node was online
        self.time_sequence_processed_in = []  # timestamps of messages decrypted (relevant for capacity limits)
        #self.time_sequence_total_in = []  # timestamps of all messages received from mixnet last layer (including dropped in incoming link)
        #self.time_sequence_total_in_client = []  # timestamps of all messages received from clients
        #self.time_sequence_total_out = []  # timestamps of all messages sent (including dropped on outgoing link)
        #self.time_sequence_true_drop_in = []  # timestamps of messages ACTUALLY dropped by this node in incoming link
        #self.time_sequence_true_drop_in_client = []  # timestamps of messages ACTUALLY dropped by this node in link from client
        #self.time_sequence_true_drop_out = []  # timestamps of messages ACTUALLY dropped by this node in outgoing link
        #self.time_sequence_delivered_all = []  # timestamps messages delivered to recipient at the end of route
        #self.time_sequence_delivered_msm = []  # timestamps of measurement messages delivered
