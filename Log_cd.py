from statistics import mean
import os
from constants import K

class Log:
    def __init__(self, config):
        self.config = config

    def create_dir(self, num_messages, num_msm_messages):

        dir_name = self.config.log_dir + "Adv_L" + str(self.config.num_layers) + "_W" + str(self.config.width_layers) +\
                   "_G" + str(self.config.num_gateways) + '_A' + str(sum(self.config.num_adversaries)) + '_T' + \
                   str(sum(self.config.num_targets)) + '_lot' + str(self.config.lottery) + "_m" + \
                   str(num_messages) + '_msm' + str(num_msm_messages) + '/'
        try:
            os.mkdir(dir_name)
        except OSError:
            print("Creation of the directory %s failed" % dir_name)
            print("Make sure a Logs/ folder exists")
        else:
            print("Successfully created the directory %s " % dir_name)
        return dir_name

    def save_simulation_parameters(self, dir_name):

        file_name = dir_name + "simulation_parameters.txt"

        with open(file_name, "w") as f:
            f.write('Gateways : ' + str(self.config.num_gateways) + ' Mixes per layer : ' + str(self.config.width_layers)
                    + ' Layers : ' + str(self.config.num_layers) + '\n')
            f.write('Num clients : ' + str(self.config.num_clients) + ' delay mix : ' + str(self.config.delay_mix)
                    + ' lottery : ' + str(self.config.lottery) + ' sim duration : ' + str(self.config.sim_duration)
                    + '\n\n')
            f.write("Capacities : " + str(self.config.list_capacity_nodes) + "\n\n")
            f.write("Drop rates incoming : " + str(self.config.list_droprates_in) + "\n\n")
            f.write("Drop rates outgoing : " + str(self.config.list_droprates_out) + "\n\n")
            f.write("Mean uptime : " + str(self.config.list_online_periods) + "\n\n")
            f.write("Mean downtime : " + str(self.config.list_offline_periods) + "\n\n")
            f.write("Corrupt : " + str(self.config.list_corrupt) + "\n\n")
            f.write("Targets : " + str(self.config.list_target) + "\n\n")
        f.close()

    def print_simulation_parameters(self, simulation):

        print('----------Simulation Parameters----------')
        print('online duration: {} and offine : {}'.format(
            simulation.config.client_online_duration, simulation.config.client_offline_duration))
        print(
            'baseline interval traffic: {} with duration : {} ; interval high traffic {} with duration : {}'.format(
                simulation.config.send_interval_baseline_traffic, simulation.config.client_baseline_volume_duration,
                simulation.config.send_interval_high_traffic, simulation.config.client_high_volume_duration))

        print('Capacities: {}'.format(simulation.config.list_capacity_nodes))
        print('Drop rates in: {}'.format(simulation.config.list_droprates_in))
        print('Drop rates out: {}'.format(simulation.config.list_droprates_out))
        print('Corrupt: {}'.format(simulation.config.list_corrupt))
        print('Mean uptime: {}'.format(simulation.config.list_online_periods))
        print('Mean downtime: {}'.format(simulation.config.list_offline_periods))

        print('\n----------Starting Simulation----------\n')

    def print_link(self, link):
        print('link id : {}'.format(link.id))
        print('link from node : {} ; to node : {} ; at layer : {}'.format(link.from_node, link.to_node,
                                                                          link.from_layer))
        # print('total samples : {} ; dropped : {}'.format(sum(link.total_samples_all), sum(link.dropped_samples_all)))
        print("samples all", mean(link.total_samples_all), link.total_samples_all)
        print("dropped all", mean(link.dropped_samples_all), link.dropped_samples_all)
        print("performance all", mean(link.measured_performance_all), link.measured_performance_all)
        print("samples msm", mean(link.total_samples_msm), link.total_samples_msm)
        print("dropped msm", mean(link.dropped_samples_msm), link.dropped_samples_msm)
        print("performance msm", mean(link.measured_performance_msm), link.measured_performance_msm)
        # print("max error all", mean(link.max_error_all), link.max_error_all)
        # print("max error msm", mean(link.max_error_msm), link.max_error_msm)
        print("error diff msm sampling", mean(link.error_diff_msm_sampling), link.error_diff_msm_sampling)
        print("-------------------------")

    def print_list_links(self, list_links):
        print('-------------------------')
        for link in list_links:
            self.print_link(link)

    def print_node(self, node):

        print('-------------------------')
        print('Node : {} ; type : {} ; layer {}'.format(node.id, node.type, node.layer))
        #        print('Percent online: {}'.format(node.percent_online))
        #        print('True performance in: {} ; dropped: {} out of {}'.format(
        #            round(node.true_performance_in, 4), sum(node.true_dropped_in), sum(node.messages_total_in)))
        #        print('All messages performance in: {} ; dropped: {} out of {} ; of which capacity drops: {}'.format(
        #            round(node.measured_performance_in, 4), sum(node.messages_dropped_in), sum(node.messages_total_in),
        #            sum(node.capacity_drops)))
        #        print('Dropped in : {} out of {} incoming messages'.format(sum(node.true_dropped_in), sum(node.messages_total_in)))
        print("incoming messages:", sum(node.counters.in_all), "true drops: ", sum(node.counters.true_drop_in_all))
        print("incoming messages from clients:", sum(node.counters.in_client_all), "true drops: ",
              sum(node.counters.true_drop_in_client_all))
        print("observed drops:", sum(node.counters.obs_drop_in_all))
        print("Measurement messages total:", sum(node.counters.in_msm), "dropped: ",
              sum(node.counters.true_drop_in_msm))
        print("observed drops:", sum(node.counters.obs_drop_in_msm))
        #        print('Measurement messages performance in: {} ; dropped: {} out of {}'.format(
        #            round(node.measured_performance_in_MEASUREMENT, 4), sum(node.messages_dropped_in_MEASUREMENT),
        #            sum(node.messages_total_in_MEASUREMENT)))
        #        print('Actual error in: {} ; Measurement sampling diff: {} ; Estimated maximum error in (measurements): {} ;'.format(
        #            round(node.actual_error_in, 4), round(node.error_in_diff_measurement_sampling, 4),
        #            round(node.maximum_error_in_MEASUREMENT, 4)))
        print('--')
        print("outgoing messages:", sum(node.counters.out_all), "true drops: ",
              sum(node.counters.true_drop_out_all))
        print("observed drops:", sum(node.counters.obs_drop_out_all))
        print("Measurement messages total:", sum(node.counters.out_msm), "dropped: ",
              sum(node.counters.true_drop_out_msm))
        print("observed drops:", sum(node.counters.obs_drop_out_msm))
        print("Messages delivered:", sum(node.counters.out_delivered_all), "measurement: ",
              sum(node.counters.out_delivered_msm))

    ######################################################

    def print_mix_event(self, description, mix_id, msg_id):
        print('{} ; mix : {} ; message : {}'.format(description, mix_id, msg_id))

    def print_message(self, msg):
        print('message type : {} ; id: {} : '.format(msg.type, msg.id))
        print("current hop : ", msg.hop, "dropped at hop : ", msg.dropped_at_hop)
        print("dropped by : ", msg.dropped_by)
        print("route : ", msg.route)
        print("trace links : ", msg.trace_links)
        print("delays : ", msg.delays)
        print("message creation : ", msg.time_created, "; bin number : ", msg.bin_nr)
        if msg.time_received >= 0.0:
            print("message received at : ", msg.time_received)
        if msg.time_dropped >= 0.0:
            print("message dropped at : ", msg.time_dropped)
        print("-------------------------")

    def print_list_messages(self, list_messages):
        print('-------------------------')
        for msg in list_messages:
            self.print_message(msg)
