from Client_cd import Client
from Network_cd import Network
from Output_dictionaries_cd import OutputDict
from Log_cd import Log
import pandas as pd
import simpy
import os


class Simulation(object):

    def __init__(self, config):
        self.env = simpy.Environment()
        self.end_event = self.env.event()  # event that triggers the end of the simulation
        self.config = config
        self.log = Log(config)
        self.network = Network(self)
        self.list_clients = self.create_clients()

    def create_clients(self):
        list_clients = []
        for client_id in range(self.config.num_clients):
            client = Client(self, client_id)
            list_clients.append(client)
        return list_clients

    def run(self):

        self.log.print_simulation_parameters(self)
        self.env.run(until=self.end_event)
        self.network.compute_stats()
        OutputDict(self.network)

        dir_name = self.log.create_dir(self.network.num_messages, self.network.num_msm_messages)
        self.log.save_simulation_parameters(dir_name)

        file_name_links = dir_name + "info_links.csv"
        file_name_nodes = dir_name + "info_nodes.csv"
        file_name_layers = dir_name + "info_layers.csv"

        df_dict_net_links = pd.DataFrame(self.network.dict_net_links)
        df_dict_net_links.to_csv(f'{file_name_links}')
        df_dict_net_nodes = pd.DataFrame(self.network.dict_net_nodes)
        df_dict_net_nodes.to_csv(f'{file_name_nodes}')
        df_dict_net_layer_stats = pd.DataFrame(self.network.dict_net_layer_stats)
        df_dict_net_layer_stats.to_csv(f'{file_name_layers}')

        for filename in [file_name_layers, file_name_links, file_name_nodes]:
            with open(filename, 'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.write('"id"' + content)

        print('----------Simulation Ended---------\n')

