class SliceHost(object):

    def __init__(self, cpu_config : int, mem_config : int, 
                cpu_percentile : dict, mem_percentile : dict, 
                cpi : dict, hwcpucycles : dict,
                cpu_avg : int, mem_avg : int, 
                oc_page_fault : int, oc_sched_wait : int):
        self.cpu_config = cpu_config
        self.mem_config = mem_config
        self.cpu_percentile = cpu_percentile
        self.mem_percentile = mem_percentile
        self.cpi=cpi
        self.hwcpucycles=hwcpucycles
        self.cpu_avg = cpu_avg
        self.mem_avg = mem_avg
        self.oc_page_fault = oc_page_fault
        self.oc_sched_wait = oc_sched_wait

    def get_cpu_percentile(self, percentile : int):
        if percentile in self.cpu_percentile:
            return self.cpu_percentile[percentile]
        return self.cpu_percentile[str(percentile)]

    def get_mem_percentile(self, percentile : int):
        if percentile in self.mem_percentile:
            return self.mem_percentile[percentile]
        return self.mem_percentile[str(percentile)]

    def get_cpi_percentile(self, percentile : int):
        if percentile in self.cpi:
            return self.cpi[percentile]
        return self.cpi[str(percentile)]

    def get_hwcpucycles_percentile(self, percentile : int):
        if percentile in self.hwcpucycles:
            return self.hwcpucycles[percentile]
        return self.hwcpucycles[str(percentile)]

    def __str__(self):
        return "SliceHost[" +  str(round(self.cpu_avg,1))  + "/" + str(round(self.get_cpu_percentile(90))) + "/" + str(int(self.cpu_config)) + " " +\
            str(round(self.mem_avg,1))  + "/" + str(round(self.get_mem_percentile(90))) + "/" + str(int(self.mem_config)) + " " +\
            "alert_oc_cpu=" + str(self.alert_oc_cpu()) + " alert_oc_mem=" + str(self.alert_oc_mem()) + "]"

    def alert_oc_cpu(self):
        return (self.oc_sched_wait>1000); # TODO value

    def alert_oc_mem(self):
        return (self.oc_page_fault>100000); # TODO value

    def dump_state_to_dict(self, dump_dict : dict, iteration : int = 0):
        for attribute, value in self.__dict__.items():
            if attribute not in dump_dict:
                dump_dict[attribute] = [0 for x in range(iteration)] # in case of new host
            dump_dict[attribute].append(value)