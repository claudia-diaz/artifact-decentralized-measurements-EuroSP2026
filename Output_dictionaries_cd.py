from constants import K
import statistics
import numpy as np

class OutputDict:

    def __init__(self, network):
        self.net = network
        self.config = network.config
        self.create_dict_net()

    def create_dict_net(self):

        # first level of dictionary corresponds to the layer, with -99 being the key for the client-gateway links
        self.net.dict_net_links[K.CLIENT] = {}  # contains the client to gateway links
        for link in self.net.dict_links[K.CLIENT]:
            self.update_link(K.CLIENT, link)

        for layer in range(self.config.num_layers + 1):
            # stats for the set of links in the layer:
            # self.net.dict_net_layer_stats[layer]["total_samples_all"][bin_nr]['samples'] = [] * W^2 links (value per link)
            # self.net.dict_net_layer_stats[layer]["total_samples_all"][bin_nr]['med'] = median of 'samples' links for that layer
            self.net.dict_net_layer_stats[layer] = {}
            self.net.dict_net_links[layer] = {}
            self.net.dict_net_nodes[layer] = {}

            # each layer contains the nodes of the layer, from 0 (gateways) to num_layers (mixes in the last layer)
            for node in self.net.dict_layers[layer]:
                self.update_node_count_bins(layer, node)
                self.update_node_count_epoch_totals(layer, node)

            # initialize dict_net_layer_stats to record the vectors with samples
            for bin_nr in range(self.config.total_bins):
                for var in ["total", "dropped", "perf", "error"]:
                    key_str = 'l' + str(layer) + '_b' + str(bin_nr) + str(var)
                    self.net.dict_net_layer_stats[layer][key_str] = {}
                    self.net.dict_net_layer_stats[layer][key_str].update({'samples': []})

            # each of these contains the links outgoing of the layer
            # -99 : clients->gateway ; 0 : gateway->mix ; ... ; num_layers : mix->gateway
            for link in self.net.dict_links[layer]:
                self.update_link(layer, link)
                for bin_nr in range(self.config.total_bins):  # collect samples per bin of each link in a layer
                    key_str = 'l' + str(layer) + '_b' + str(bin_nr) + 'total'
                    self.net.dict_net_layer_stats[layer][key_str]['samples'].append(link.total_samples_msm[bin_nr])
                    key_str = 'l' + str(layer) + '_b' + str(bin_nr) + 'dropped'
                    self.net.dict_net_layer_stats[layer][key_str]['samples'].append(link.dropped_samples_msm[bin_nr])
                    key_str = 'l' + str(layer) + '_b' + str(bin_nr) + 'perf'
                    self.net.dict_net_layer_stats[layer][key_str]['samples'].append(link.measured_performance_msm[bin_nr])
                    key_str = 'l' + str(layer) + '_b' + str(bin_nr) + 'error'
                    self.net.dict_net_layer_stats[layer][key_str]['samples'].append(link.max_error_msm[bin_nr])

            # compute distribution of performance across links in a layer
            self.update_stats_layer(layer)

    def update_link(self, layer, link):
        self.net.dict_net_links[layer][link.id] = {}
        self.net.dict_net_links[layer][link.id].update({"total_samples_all": link.total_samples_all})
        self.net.dict_net_links[layer][link.id].update({"total_samples_msm": link.total_samples_msm})
        self.net.dict_net_links[layer][link.id].update({"dropped_samples_all": link.dropped_samples_all})
        self.net.dict_net_links[layer][link.id].update({"dropped_samples_msm": link.dropped_samples_msm})
        self.net.dict_net_links[layer][link.id].update({"measured_performance_all": link.measured_performance_all})
        self.net.dict_net_links[layer][link.id].update({"measured_performance_msm": link.measured_performance_msm})
        self.net.dict_net_links[layer][link.id].update({"max_error_all": link.max_error_all})
        self.net.dict_net_links[layer][link.id].update({"max_error_msm": link.max_error_msm})
        self.net.dict_net_links[layer][link.id].update({"error_diff_msm_sampling": link.error_diff_msm_sampling})
        self.net.dict_net_links[layer][link.id].update({"drops_assigned_pred_all": link.drops_assigned_pred_all})
        self.net.dict_net_links[layer][link.id].update({"drops_assigned_suc_all": link.drops_assigned_suc_all})
        self.net.dict_net_links[layer][link.id].update({"drops_assigned_pred_msm": link.drops_assigned_pred_msm})
        self.net.dict_net_links[layer][link.id].update({"drops_assigned_suc_msm": link.drops_assigned_suc_msm})
        self.net.dict_net_links[layer][link.id].update({"anomaly": link.anomaly})
        self.net.dict_net_links[layer][link.id].update({"layer_overload": link.layer_overload})

    def update_node_count_bins(self, layer, node):

        self.net.dict_net_nodes[layer][node.id] = {}
        self.net.dict_net_nodes[layer][node.id].update({"id": node.id})
        self.net.dict_net_nodes[layer][node.id].update({"type": node.type})
        self.net.dict_net_nodes[layer][node.id].update({"layer": node.layer})
        self.net.dict_net_nodes[layer][node.id].update({"droprate_in": node.droprate_in})
        self.net.dict_net_nodes[layer][node.id].update({"droprate_out": node.droprate_out})
        self.net.dict_net_nodes[layer][node.id].update({"online_mean_period": node.online_mean_period})
        self.net.dict_net_nodes[layer][node.id].update({"offline_mean_period": node.offline_mean_period})
        self.net.dict_net_nodes[layer][node.id].update({"capacity": node.capacity})
        self.net.dict_net_nodes[layer][node.id].update({"corrupt": node.corrupt})
        self.net.dict_net_nodes[layer][node.id].update({"target": node.target})

        self.net.dict_net_nodes[layer][node.id].update({"in_all": node.counters.in_all})
        self.net.dict_net_nodes[layer][node.id].update({"in_msm": node.counters.in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"out_all": node.counters.out_all})
        self.net.dict_net_nodes[layer][node.id].update({"out_msm": node.counters.out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"in_client_all": node.counters.in_client_all})
        self.net.dict_net_nodes[layer][node.id].update({"in_client_msm": node.counters.in_client_msm})
        self.net.dict_net_nodes[layer][node.id].update({"out_delivered_all": node.counters.out_delivered_all})
        self.net.dict_net_nodes[layer][node.id].update({"out_delivered_msm": node.counters.out_delivered_msm})

        self.net.dict_net_nodes[layer][node.id].update({"true_drop_in_client_all": node.counters.true_drop_in_client_all})
        self.net.dict_net_nodes[layer][node.id].update({"true_drop_in_client_msm": node.counters.true_drop_in_client_msm})
        self.net.dict_net_nodes[layer][node.id].update({"true_drop_in_all": node.counters.true_drop_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"true_drop_in_msm": node.counters.true_drop_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"true_drop_out_all": node.counters.true_drop_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"true_drop_out_msm": node.counters.true_drop_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"obs_drop_in_client_all": node.counters.obs_drop_in_client_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_drop_in_client_msm": node.counters.obs_drop_in_client_msm})
        self.net.dict_net_nodes[layer][node.id].update({"obs_drop_in_all": node.counters.obs_drop_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_drop_in_msm": node.counters.obs_drop_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"obs_drop_out_all": node.counters.obs_drop_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_drop_out_msm": node.counters.obs_drop_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"filter_drop_in_all": node.counters.filter_drop_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"filter_drop_in_msm": node.counters.filter_drop_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"filter_drop_out_all": node.counters.filter_drop_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"filter_drop_out_msm": node.counters.filter_drop_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"frac_msm_in_client": node.counters.frac_msm_in_client})
        self.net.dict_net_nodes[layer][node.id].update({"frac_msm_out_delivered": node.counters.frac_msm_out_delivered})

        self.net.dict_net_nodes[layer][node.id].update({"true_perf_in_client_all": node.counters.true_perf_in_client_all})
        self.net.dict_net_nodes[layer][node.id].update({"true_perf_in_client_msm": node.counters.true_perf_in_client_msm})
        self.net.dict_net_nodes[layer][node.id].update({"true_perf_in_all": node.counters.true_perf_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"true_perf_in_msm": node.counters.true_perf_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"true_perf_out_all": node.counters.true_perf_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"true_perf_out_msm": node.counters.true_perf_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_in_client_all": node.counters.obs_perf_in_client_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_in_client_msm": node.counters.obs_perf_in_client_msm})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_in_all": node.counters.obs_perf_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_in_msm": node.counters.obs_perf_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_out_all": node.counters.obs_perf_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_out_msm": node.counters.obs_perf_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"filter_perf_in_all": node.counters.filter_perf_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"filter_perf_in_msm": node.counters.filter_perf_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"filter_perf_out_all": node.counters.filter_perf_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"filter_perf_out_msm": node.counters.filter_perf_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"no_attack_perf_in_all": node.counters.no_attack_perf_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"no_attack_perf_in_msm": node.counters.no_attack_perf_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"no_attack_perf_out_all": node.counters.no_attack_perf_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"no_attack_perf_out_msm": node.counters.no_attack_perf_out_msm})

        self.net.dict_net_nodes[layer][node.id].update({"frac_uptime": node.counters.frac_uptime})
        self.net.dict_net_nodes[layer][node.id].update({"marked_offline": node.counters.marked_offline})
        self.net.dict_net_nodes[layer][node.id].update({"marked_faulty": node.counters.marked_faulty})
        self.net.dict_net_nodes[layer][node.id].update({"anomaly_in": node.counters.anomaly_in})
        self.net.dict_net_nodes[layer][node.id].update({"anomaly_out": node.counters.anomaly_out})

        med_in_all = []
        med_in_msm = []
        med_out_all = []
        med_out_msm = []
        for bin_nr in range(self.config.total_bins):
                med_in_all.append(node.perf_dict[bin_nr]['in_all']['med'])
                med_out_all.append(node.perf_dict[bin_nr]['out_all']['med'])
                med_in_msm.append(node.perf_dict[bin_nr]['in_msm']['med'])
                med_out_msm.append(node.perf_dict[bin_nr]['out_msm']['med'])
        self.net.dict_net_nodes[layer][node.id].update({"med_perf_in_all": med_in_all})
        self.net.dict_net_nodes[layer][node.id].update({"med_perf_in_msm": med_in_msm})
        self.net.dict_net_nodes[layer][node.id].update({"med_perf_out_all": med_out_all})
        self.net.dict_net_nodes[layer][node.id].update({"med_perf_out_msm": med_out_msm})

    def update_node_count_epoch_totals(self, layer, node):

        self.net.dict_net_nodes[layer][node.id].update({"true_perf_all": node.counters.true_perf_all})
        self.net.dict_net_nodes[layer][node.id].update({"filter_perf_all": node.counters.filter_perf_all})
        self.net.dict_net_nodes[layer][node.id].update({"no_attack_perf_all": node.counters.no_attack_perf_all})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_all": node.counters.obs_perf_all})

        self.net.dict_net_nodes[layer][node.id].update({"true_perf_msm": node.counters.true_perf_msm})
        self.net.dict_net_nodes[layer][node.id].update({"filter_perf_msm": node.counters.filter_perf_msm})
        self.net.dict_net_nodes[layer][node.id].update({"no_attack_perf_msm": node.counters.no_attack_perf_msm})
        self.net.dict_net_nodes[layer][node.id].update({"obs_perf_msm": node.counters.obs_perf_msm})

    def update_stats_layer(self, layer):

        # obtain statistics per bin and per layer for the set of links
        for bin_nr in range(self.config.total_bins):
            for var in ["total", "dropped", "perf", "error"]:
                key_str = 'l' + str(layer) + '_b' + str(bin_nr) + str(var)
                med = statistics.median(self.net.dict_net_layer_stats[layer][key_str]['samples'])
                avg = statistics.mean(self.net.dict_net_layer_stats[layer][key_str]['samples'])
                std = statistics.stdev(self.net.dict_net_layer_stats[layer][key_str]['samples'])
                p0 = min(self.net.dict_net_layer_stats[layer][key_str]['samples'])
                p100 = max(self.net.dict_net_layer_stats[layer][key_str]['samples'])
                p25 = np.percentile(self.net.dict_net_layer_stats[layer][key_str]['samples'], 25)
                p33 = np.percentile(self.net.dict_net_layer_stats[layer][key_str]['samples'], 33.33)
                p66 = np.percentile(self.net.dict_net_layer_stats[layer][key_str]['samples'], 66.67)
                p75 = np.percentile(self.net.dict_net_layer_stats[layer][key_str]['samples'], 75)
                self.net.dict_net_layer_stats[layer][key_str].update({'avg': avg, 'std': std})
                self.net.dict_net_layer_stats[layer][key_str].update({'med': med, 'min': p0, 'max': p100})
                self.net.dict_net_layer_stats[layer][key_str].update({'p25': p25, 'p33': p33, 'p66': p66, 'p75': p75})
                # if layer is overloaded for the bin, mark all layers as overloaded and update the dictionary
                if var == 'perf' and med < self.config.min_perf:
                    for link in self.net.dict_links[layer]:
                        link.layer_overload[bin_nr] = 1
                        self.net.dict_net_links[layer][link.id].update({"layer_overload": link.layer_overload})

