from Simulation_cd import Simulation
#from Eval_cross_check import Eval_cross_check
from Configuration_cd import Configuration
#from Log_cd import Log
import time


def main():

    #sets_adversaries = [[0, 12, 12, 12], [0, 8, 8, 8], [0, 4, 4, 4], [0, 2, 2, 2], [0, 1, 1, 1]]
    sets_targets = [[0, 0, 4, 0], [0, 0, 8, 0], [0, 0, 16, 0], [0, 0, 32, 0]]
    #set_prob_drop_attack = [1.0, 0.5, 0.1, 0.05, 0.02, 0.01]
    sets_adversaries = [[0, 32, 0, 0], [0, 0, 0, 32], [0, 32, 0, 32], [0, 16, 0, 16],
                        [0, 16, 0, 0], [0, 0, 0, 16], [0, 8, 0, 8]]

    #set_prob_drop_attack = [1.0, 0.5, 0.1, 0.02]
    #sets_adversaries = [[0, 0, 0, 0]]
    #sets_targets = [[0, 0, 0, 0]]
    #set_prob_drop_attack = [0.0] * 10

    set_prob_drop_attack = [1.0]

    for adversaries in sets_adversaries:
        for targets in sets_targets:
            for prob_drop_attack in set_prob_drop_attack:
                config = Configuration(adversaries, targets, prob_drop_attack)
                simulation = Simulation(config)
                simulation.run()

    # print some summary variables
    # print("-------------------------")
    # print("Total number of messages routed:", simulation.network.num_messages)
    # print("Simulation runtime:", round(time.time() - config.start_time, 1), "seconds")
    # print("-------------------------")
    # uncomment for cross-validation of all node counts using the list of messages
    # ev2 = Eval_cross_check(simulation)
    # for i in range(config.total_nodes):
    #    node1 = simulation.network.list_nodes[i]
    #    node2 = ev2.list_nodes[i]
    #    ev2.compareCounts(node1.count, node2.count)


if __name__ == "__main__":
    main()
