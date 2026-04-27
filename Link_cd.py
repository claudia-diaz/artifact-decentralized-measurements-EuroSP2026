
class Link:
    def __init__(self, from_node, to_node, from_layer, total_bins):
        # link id and position
        self.from_node = from_node
        self.to_node = to_node
        self.from_layer = from_layer
        self.id = "%d_%d_%d" % (self.from_layer, self.from_node, self.to_node)
        # samples total and dropped
        self.total_samples_all = [0] * total_bins
        self.total_samples_msm = [0] * total_bins
        self.dropped_samples_all = [0] * total_bins
        self.dropped_samples_msm = [0] * total_bins
        # performance and sampling error
        self.measured_performance_all = [0] * total_bins
        self.measured_performance_msm = [0] * total_bins
        self.max_error_all = [1.0] * total_bins
        self.max_error_msm = [1.0] * total_bins
        self.error_diff_msm_sampling = [1.0] * total_bins  # diff performance estimated: msm messages vs all messages
        # filtered counts
        self.drops_assigned_pred_all = [0] * total_bins
        self.drops_assigned_suc_all = [0] * total_bins
        self.drops_assigned_pred_msm = [0] * total_bins
        self.drops_assigned_suc_msm = [0] * total_bins
        self.anomaly = [0] * total_bins
        self.layer_overload = [0] * total_bins

