import math
import statistics
import numpy as np
from Mix_cd import Mix
from Link_cd import Link
from numpy.random import exponential
import random
from constants import K


class Network:

    def __init__(self, simulation):
        self.simulation = simulation
        self.env = simulation.env
        self.config = simulation.config
        self.list_nodes = []  # list of Mix objects, contains num_gateways gateways + num_layers*width_layers mixes
        #self.list_messages = []  # list of Message objects for all messages sent through the system
        self.num_messages = 0
        self.num_msm_messages = 0
        self.dict_layers = {}  # 0: [list of gateways], 1:[list of mixes in layer 1], 2:[list of mixes in layer 2], ...
        self.dict_links = {}  # -99: [list of links client->gateways] ; 0: [list of links gateway->1st layer], 1:[list of links layers 1->2], ...
        self.dict_net_links = {}  # dictionary used to log the links' information for saving into a cvs file and making graphs
        self.dict_net_nodes = {}  # dictionary used to log the nodes' information for saving into a cvs file and making graphs
        self.dict_net_layer_stats = {}  # dictionary used to log aggregate info (stats) for the set of links in each layer
        self.create_network()

    def create_network(self):

        # create gateways
        node_index = 0
        layer = 0
        mix_type = K.GATEWAY
        self.dict_layers[layer] = []
        for i in range(self.config.num_gateways):
            gateway = Mix(self.simulation, mix_type, node_index, layer)
            self.list_nodes.append(gateway)
            self.dict_layers[layer].append(gateway)
            node_index += 1

        # create the layers of the mixnet
        mix_type = K.MIX
        for layer in range(1, self.config.num_layers + 1):
            self.dict_layers[layer] = []
            for i in range(self.config.width_layers):
                mix = Mix(self.simulation, mix_type, node_index, layer)
                self.list_nodes.append(mix)
                self.dict_layers[layer].append(mix)
                node_index += 1

        # create the dictionary of links: from client to gateways and from gateways to mixes in layer 1
        self.dict_links[K.CLIENT] = []
        self.dict_links[0] = []
        for gateway in self.dict_layers[0]:
            link = Link(K.CLIENT, gateway.id, K.CLIENT, self.config.total_bins)
            self.dict_links[K.CLIENT].append(link)
            gateway.client_links.append(link)
            for mix_successor in self.dict_layers[1]:
                link = Link(gateway.id, mix_successor.id, 0, self.config.total_bins)
                self.dict_links[0].append(link)
                gateway.outgoing_links.append(link)
                mix_successor.incoming_links.append(link)

        # links between mixes
        for layer in range(1, self.config.num_layers):
            self.dict_links[layer] = []
            for mix_predecessor in self.dict_layers[layer]:
                for mix_successor in self.dict_layers[layer+1]:
                    link = Link(mix_predecessor.id, mix_successor.id, layer, self.config.total_bins)
                    self.dict_links[layer].append(link)
                    mix_predecessor.outgoing_links.append(link)
                    mix_successor.incoming_links.append(link)

        # links from last mixes to gateways
        self.dict_links[self.config.num_layers] = []
        for mix_predecessor in self.dict_layers[self.config.num_layers]:
            for gateway in self.dict_layers[0]:
                link = Link(mix_predecessor.id, gateway.id, self.config.num_layers, self.config.total_bins)
                self.dict_links[self.config.num_layers].append(link)
                mix_predecessor.outgoing_links.append(link)
                gateway.incoming_links.append(link)

    def get_acked_route(self, msg_type):

        route = []
        gateway_sender = random.randint(0, self.config.num_gateways - 1)  # sender's gateway excludes gateway zero
        route.append(gateway_sender)
        for layer in range(1, self.config.num_layers + 1):  # route through mixes of 1st leg of measurement message
            mix = random.choice(self.dict_layers[layer])
            route.append(mix.id)

        if msg_type == K.MSG_REAL:
            gateway_rec = random.randint(0, self.config.num_gateways - 1)  # randomly choose recipient gateway
            route.append(gateway_rec)  # first leg of measurement message hitting the sender's gateway again
        else:  # keep the same gateway as before (message loops back)
            route.append(gateway_sender)  # first leg of measurement message hitting the sender's gateway again

        for layer in range(1, self.config.num_layers + 1):  # route of the ack (second leg of the message)
            mix = random.choice(self.dict_layers[layer])
            route.append(mix.id)
        if msg_type == K.MSG_REAL or msg_type == K.MSG_DUMMY:
            route.append(route[0])  # ack back to sender's gateway
        elif msg_type == K.MSG_MEASUREMENT:
            route.append(K.GW_BROADCAST)  # gateway 0 is for the blockchain/broadcast, measurement messages arrive there
        return route

    def get_delays_route(self):

        delays = [K.PROCESSING_TIME_GATEWAYS]  # delay of sender's gateway
        for i in range(self.config.num_layers):  # delays of the forward (1st leg) message
            delays.append(exponential(self.config.delay_mix))
        delays.append(K.PROCESSING_TIME_GATEWAYS)  # first leg of message arrives to gateway, which sends back ack
        for i in range(self.config.num_layers):  # delays of the ack (2nd leg) message
            delays.append(exponential(self.config.delay_mix))
        delays.append(K.PROCESSING_TIME_GATEWAYS)  # ack arrives to the sender's gateway
        return delays

    def route_message(self, msg):

        node = self.list_nodes[msg.route[0]]
        self.env.process(node.receive_msg(msg))

    def compute_stats(self):

        # compute stats for the links of all layers
        for link in self.dict_links[K.CLIENT]:
            self.compute_stats_link(link)
        for layer in range(self.config.num_layers + 1):
            for link in self.dict_links[layer]:
                self.compute_stats_link(link)

        # compute observed drops (per bin) for node : aggregated drops in in/out/client links
        for node in self.list_nodes:
            self.set_fraction_uptime(node)
            self.set_observed_drops_node(node)
            self.create_dict_performance_node(node)
            self.set_flags_performance(node)
        # set the filtered drop counts for all nodes
        self.set_filtered_counts()
        # compute final stats per node
        for node in self.list_nodes:
            self.compute_stats_node(node)

    def set_fraction_uptime(self, node):
        for bin_nr in range(self.config.total_bins):
            node.counters.frac_uptime[bin_nr] = node.counters.uptime[bin_nr] / self.config.bin_width

    def set_observed_drops_node(self, node):

        if node.type == K.GATEWAY:
            link = node.client_links[0]
            node.counters.obs_drop_in_client_all = link.dropped_samples_all
            node.counters.obs_drop_in_client_msm = link.dropped_samples_msm
            #for bin_nr in range(self.config.total_bins):
            #    node.counters.obs_drop_in_client_all[bin_nr] = link.dropped_samples_all[bin_nr]
            #    node.counters.obs_drop_in_client_msm[bin_nr] = link.dropped_samples_msm[bin_nr]

        for link in node.incoming_links:
            for bin_nr in range(self.config.total_bins):
                node.counters.obs_drop_in_all[bin_nr] += link.dropped_samples_all[bin_nr]
                node.counters.obs_drop_in_msm[bin_nr] += link.dropped_samples_msm[bin_nr]

        for link in node.outgoing_links:
            for bin_nr in range(self.config.total_bins):
                node.counters.obs_drop_out_all[bin_nr] += link.dropped_samples_all[bin_nr]
                node.counters.obs_drop_out_msm[bin_nr] += link.dropped_samples_msm[bin_nr]

    def create_dict_performance_node(self, node):

        for bin_nr in range(self.config.total_bins):
            node.perf_dict[bin_nr] = {}
            node.perf_dict[bin_nr].update({'in_all': {}})
            node.perf_dict[bin_nr].update({'in_msm': {}})
            node.perf_dict[bin_nr].update({'out_all': {}})
            node.perf_dict[bin_nr].update({'out_msm': {}})
            node.perf_dict[bin_nr]['in_all'].update({'samples': []})
            node.perf_dict[bin_nr]['in_msm'].update({'samples': []})
            node.perf_dict[bin_nr]['out_all'].update({'samples': []})
            node.perf_dict[bin_nr]['out_msm'].update({'samples': []})

            for link in node.incoming_links:
                node.perf_dict[bin_nr]['in_all']['samples'].append(link.measured_performance_all[bin_nr])
                node.perf_dict[bin_nr]['in_msm']['samples'].append(link.measured_performance_msm[bin_nr])
            for link in node.outgoing_links:
                node.perf_dict[bin_nr]['out_all']['samples'].append(link.measured_performance_all[bin_nr])
                node.perf_dict[bin_nr]['out_msm']['samples'].append(link.measured_performance_msm[bin_nr])

            for v1 in ['in_all', 'in_msm', 'out_all', 'out_msm']:
                node.perf_dict[bin_nr][v1].update({'med': statistics.median(node.perf_dict[bin_nr][v1]['samples'])})
                node.perf_dict[bin_nr][v1].update({'avg': statistics.mean(node.perf_dict[bin_nr][v1]['samples'])})
                node.perf_dict[bin_nr][v1].update({'p66': np.percentile(node.perf_dict[bin_nr][v1]['samples'], 66.67)})
                node.perf_dict[bin_nr][v1].update({'p75': np.percentile(node.perf_dict[bin_nr][v1]['samples'], 75)})
                node.perf_dict[bin_nr][v1].update({'max': max(node.perf_dict[bin_nr][v1]['samples'])})
                node.perf_dict[bin_nr][v1].update({'std': statistics.stdev(node.perf_dict[bin_nr][v1]['samples'])})

    def set_flags_performance(self, node):

        for bin_nr in range(self.config.total_bins):
            # change in_all/out_all to in_msm/out_msm for using only msm messages for the decision
            if node.perf_dict[bin_nr]['in_msm']['med'] < self.config.min_perf:
                node.counters.marked_offline[bin_nr] = 1  # mark node as offline for the bin (affects incoming links)
            if node.perf_dict[bin_nr]['out_msm']['med'] < self.config.min_perf:
                node.counters.marked_faulty[bin_nr] = 1  # mark node as faulty for the bin (affects outgoing links)

    def set_filtered_counts(self):

        for layer in range(self.config.num_layers + 1):
            for link in self.dict_links[layer]:
                predecessor = self.list_nodes[link.from_node]
                successor = self.list_nodes[link.to_node]
                for bin_nr in range(self.config.total_bins):

                    # both predecessor and successor are marked as problematic
                    if predecessor.counters.marked_faulty[bin_nr] == 1 and successor.counters.marked_offline[bin_nr] == 1:
                        # predecessor has zero outputs in bin (fully offline), thus takes all the blame
                        if predecessor.counters.out_msm[bin_nr] == 0:
                            link.drops_assigned_pred_all[bin_nr] += link.dropped_samples_all[bin_nr]
                            link.drops_assigned_pred_msm[bin_nr] += link.dropped_samples_msm[bin_nr]
                        # successor has zero outputs in bin (fully offline), thus takes all the blame
                        elif successor.counters.out_msm[bin_nr] == 0:  # zero output in bin, fully offline
                            link.drops_assigned_suc_all[bin_nr] += link.dropped_samples_all[bin_nr]
                            link.drops_assigned_suc_msm[bin_nr] += link.dropped_samples_msm[bin_nr]
                        # some output from both nodes, both nodes partially operational, blame is allocated 50-50
                        else:
                            link.drops_assigned_pred_all[bin_nr] += link.dropped_samples_all[bin_nr] * (1 - self.config.beta_sim)
                            link.drops_assigned_suc_all[bin_nr] += link.dropped_samples_all[bin_nr] * self.config.beta_sim
                            link.drops_assigned_pred_msm[bin_nr] += link.dropped_samples_msm[bin_nr] * (1 - self.config.beta_sim)
                            link.drops_assigned_suc_msm[bin_nr] += link.dropped_samples_msm[bin_nr] * self.config.beta_sim

                    # predecessor is offline, successor is online, predecessor takes all the blame
                    elif predecessor.counters.marked_faulty[bin_nr] == 1 and successor.counters.marked_offline[bin_nr] == 0:
                        link.drops_assigned_pred_all[bin_nr] += link.dropped_samples_all[bin_nr]
                        link.drops_assigned_pred_msm[bin_nr] += link.dropped_samples_msm[bin_nr]

                    # successor is offline, predecessor is online, successor takes all the blame
                    elif predecessor.counters.marked_faulty[bin_nr] == 0 and successor.counters.marked_offline[bin_nr] == 1:
                        link.drops_assigned_suc_all[bin_nr] += link.dropped_samples_all[bin_nr]
                        link.drops_assigned_suc_msm[bin_nr] += link.dropped_samples_msm[bin_nr]

                    # both are considered operational
                    elif predecessor.counters.marked_faulty[bin_nr] == 0 and successor.counters.marked_offline[bin_nr] == 0:
                        link.drops_assigned_pred_all[bin_nr] += link.dropped_samples_all[bin_nr] * (1 - self.config.beta_sim)
                        link.drops_assigned_suc_all[bin_nr] += link.dropped_samples_all[bin_nr] * self.config.beta_sim
                        link.drops_assigned_pred_msm[bin_nr] += link.dropped_samples_msm[bin_nr] * (1 - self.config.beta_sim)
                        link.drops_assigned_suc_msm[bin_nr] += link.dropped_samples_msm[bin_nr] * self.config.beta_sim

                        # check for anomalies : both online but performance of link is too low
                        perf_link = link.measured_performance_msm[bin_nr]  # change to measured_performance_msm
                        max_error = link.max_error_msm[bin_nr]  # change to max_error_msm (for msm messages only)
                        if perf_link < (self.config.min_perf - max_error):
                            link.anomaly[bin_nr] = 1
                            predecessor.counters.anomaly_out.append(successor.id)
                            successor.counters.anomaly_in.append(predecessor.id)

                    # set filtered counts in the nodes as well
                    predecessor.counters.filter_drop_out_all[bin_nr] += link.drops_assigned_pred_all[bin_nr]
                    predecessor.counters.filter_drop_out_msm[bin_nr] += link.drops_assigned_pred_msm[bin_nr]
                    successor.counters.filter_drop_in_all[bin_nr] += link.drops_assigned_suc_all[bin_nr]
                    successor.counters.filter_drop_in_msm[bin_nr] += link.drops_assigned_suc_msm[bin_nr]

    def compute_stats_node(self, node):

        node.counters.frac_msm_in_client = self.config.compute_fraction_lists(node.counters.in_client_msm, node.counters.in_client_all)
        node.counters.frac_msm_out_delivered = self.config.compute_fraction_lists(node.counters.out_delivered_msm, node.counters.out_delivered_all)

        node.counters.true_perf_in_client_all = self.config.compute_one_minus_fraction_lists(node.counters.true_drop_in_client_all, node.counters.in_client_all)
        node.counters.true_perf_in_client_msm = self.config.compute_one_minus_fraction_lists(node.counters.true_drop_in_client_msm, node.counters.in_client_msm)
        node.counters.true_perf_in_all = self.config.compute_one_minus_fraction_lists(node.counters.true_drop_in_all, node.counters.in_all)
        node.counters.true_perf_in_msm = self.config.compute_one_minus_fraction_lists(node.counters.true_drop_in_msm, node.counters.in_msm)
        node.counters.true_perf_out_all = self.config.compute_one_minus_fraction_lists(node.counters.true_drop_out_all,node.counters.out_all)
        node.counters.true_perf_out_msm = self.config.compute_one_minus_fraction_lists(node.counters.true_drop_out_msm,node.counters.out_msm)

        node.counters.obs_perf_in_client_all = self.config.compute_one_minus_fraction_lists(node.counters.obs_drop_in_client_all, node.counters.in_client_all)
        node.counters.obs_perf_in_client_msm = self.config.compute_one_minus_fraction_lists(node.counters.obs_drop_in_client_msm, node.counters.in_client_msm)
        node.counters.obs_perf_in_all = self.config.compute_one_minus_fraction_lists(node.counters.obs_drop_in_all, node.counters.in_all)
        node.counters.obs_perf_in_msm = self.config.compute_one_minus_fraction_lists(node.counters.obs_drop_in_msm, node.counters.in_msm)
        node.counters.obs_perf_out_all = self.config.compute_one_minus_fraction_lists(node.counters.obs_drop_out_all, node.counters.out_all)
        node.counters.obs_perf_out_msm = self.config.compute_one_minus_fraction_lists(node.counters.obs_drop_out_msm, node.counters.out_msm)

        filter_denom_in_all = np.subtract(node.counters.in_all, node.counters.true_drop_in_all)
        filter_denom_in_all = np.add(filter_denom_in_all, node.counters.filter_drop_in_all)
        filter_denom_in_msm = np.subtract(node.counters.in_msm, node.counters.true_drop_in_msm)
        filter_denom_in_msm = np.add(filter_denom_in_msm, node.counters.filter_drop_in_msm)

        filter_denom_out_all = np.subtract(node.counters.out_all, node.counters.obs_drop_out_all)
        filter_denom_out_all = np.add(filter_denom_out_all, node.counters.filter_drop_out_all)
        filter_denom_out_msm = np.subtract(node.counters.out_msm, node.counters.obs_drop_out_msm)
        filter_denom_out_msm = np.add(filter_denom_out_msm, node.counters.filter_drop_out_msm)

        node.counters.filter_perf_in_all = self.config.compute_one_minus_fraction_lists(node.counters.filter_drop_in_all, filter_denom_in_all)
        node.counters.filter_perf_in_msm = self.config.compute_one_minus_fraction_lists(node.counters.filter_drop_in_msm, filter_denom_in_msm)
        node.counters.filter_perf_out_all = self.config.compute_one_minus_fraction_lists(node.counters.filter_drop_out_all, filter_denom_out_all)
        node.counters.filter_perf_out_msm = self.config.compute_one_minus_fraction_lists(node.counters.filter_drop_out_msm, filter_denom_out_msm)

        list_diff_attack_in_all = np.subtract(node.counters.true_drop_in_all, node.counters.attack_drop_in_all)
        list_diff_attack_in_msm = np.subtract(node.counters.true_drop_in_msm, node.counters.attack_drop_in_msm)
        list_diff_attack_out_all = np.subtract(node.counters.true_drop_out_all, node.counters.attack_drop_out_all)
        list_diff_attack_out_msm = np.subtract(node.counters.true_drop_out_msm, node.counters.attack_drop_out_msm)

        node.counters.no_attack_perf_in_all = self.config.compute_one_minus_fraction_lists(list_diff_attack_in_all, node.counters.in_all)
        node.counters.no_attack_perf_in_msm = self.config.compute_one_minus_fraction_lists(list_diff_attack_in_msm, node.counters.in_msm)
        node.counters.no_attack_perf_out_all = self.config.compute_one_minus_fraction_lists(list_diff_attack_out_all, node.counters.out_all)
        node.counters.no_attack_perf_out_msm = self.config.compute_one_minus_fraction_lists(list_diff_attack_out_msm, node.counters.out_msm)

        ###################
        diff_attack_in_all = sum(node.counters.true_drop_in_all) - sum(node.counters.attack_drop_in_all)
        diff_attack_in_msm = sum(node.counters.true_drop_in_msm) - sum(node.counters.attack_drop_in_msm)
        diff_attack_out_all = sum(node.counters.true_drop_out_all) - sum(node.counters.attack_drop_out_all)
        diff_attack_out_msm = sum(node.counters.true_drop_out_msm) - sum(node.counters.attack_drop_out_msm)

        if sum(node.counters.in_all) > 0:
            node.counters.true_perf_all = 1 - (sum(node.counters.true_drop_in_all) + sum(node.counters.true_drop_out_all)) / sum(node.counters.in_all)
            node.counters.obs_perf_all = 1 - (sum(node.counters.obs_drop_in_all)) / sum(node.counters.in_all)
            node.counters.no_attack_perf_all = 1 - (diff_attack_in_all + diff_attack_out_all) / sum(node.counters.in_all)
        if sum(node.counters.in_msm) > 0:
            node.counters.true_perf_msm = 1 - (sum(node.counters.true_drop_in_msm) + sum(node.counters.true_drop_out_msm)) / sum(node.counters.in_msm)
            node.counters.obs_perf_msm = 1 - sum(node.counters.obs_drop_in_msm) / sum(node.counters.in_msm)
            node.counters.no_attack_perf_msm = 1 - (diff_attack_in_msm + diff_attack_out_msm) / sum(node.counters.in_msm)

        if sum(filter_denom_in_all) > 0:
            node.counters.filter_perf_all = 1 - (sum(node.counters.filter_drop_in_all) + sum(node.counters.filter_drop_out_all)) / sum(filter_denom_in_all)
        if sum(filter_denom_in_msm) > 0:
            node.counters.filter_perf_msm = 1 - (sum(node.counters.filter_drop_in_msm) + sum(node.counters.filter_drop_out_msm)) / sum(filter_denom_in_msm)

    def compute_stats_link(self, link):

        link.measured_performance_all = self.config.compute_one_minus_fraction_lists(link.dropped_samples_all, link.total_samples_all)
        link.measured_performance_msm = self.config.compute_one_minus_fraction_lists(link.dropped_samples_msm, link.total_samples_msm)
        link.max_error_all = self.config.compute_max_error_bin(link.measured_performance_all, link.total_samples_all)
        link.max_error_msm = self.config.compute_max_error_bin(link.measured_performance_msm, link.total_samples_msm)
        for bin_nr in range(self.config.total_bins):
            link.error_diff_msm_sampling[bin_nr] = link.measured_performance_msm[bin_nr] - link.measured_performance_all[bin_nr]
