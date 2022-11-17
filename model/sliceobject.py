class SliceObject(object):

    def __init__(self, cpu_config : int, mem_config : int, 
            cpu_percentile : dict, mem_percentile : dict, 
            cpu_avg : int, mem_avg : int, 
            cpu_std : int, mem_std : int,
            cpu_max : int, mem_max : int,
            oc_page_fault : int, oc_page_fault_std : int,
            oc_sched_wait : int, oc_sched_wait_std : int,
            cpi : dict, hwcpucycles : dict,
            number_of_values :int,
            ):
        self.cpu_config = cpu_config
        self.mem_config = mem_config
        self.cpu_percentile = cpu_percentile
        self.mem_percentile = mem_percentile
        self.cpu_avg = cpu_avg
        self.mem_avg = mem_avg
        self.cpu_std = cpu_std
        self.mem_std = mem_std
        self.cpu_max = cpu_max
        self.mem_max = mem_max
        self.oc_page_fault = oc_page_fault
        self.oc_page_fault_std = oc_page_fault_std
        self.oc_sched_wait = oc_sched_wait
        self.oc_sched_wait_std = oc_sched_wait_std
        self.cpi=cpi
        self.hwcpucycles=hwcpucycles
        self.number_of_values = number_of_values

    def get_cpu_config(self):
        return self.cpu_config

    def get_mem_config(self):
        return self.mem_config

    def get_cpu_avg(self):
        return self.cpu_avg
    
    def get_mem_avg(self):
        return self.mem_avg

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
