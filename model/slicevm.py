class SliceVm(object):

    def __init__(self, cpu_config : int, mem_config : int, 
                cpu_percentile : dict, mem_percentile : dict, 
                cpu_avg : int, mem_avg : int, 
                cpu_std : int, mem_std : int, 
                oc_page_fault : int, oc_page_fault_std : int,
                oc_sched_wait : int, oc_sched_wait_std : int,
                number_of_values :int,
                cpu_state : int = 0, mem_state : int = 0):
        self.cpu_config = cpu_config
        self.mem_config = mem_config
        self.cpu_percentile = cpu_percentile
        self.mem_percentile = mem_percentile
        self.cpu_avg = cpu_avg
        self.mem_avg = mem_avg
        self.cpu_std = cpu_std
        self.mem_std = mem_std
        self.oc_page_fault = oc_page_fault
        self.oc_page_fault_std = oc_page_fault_std
        self.oc_sched_wait = oc_sched_wait
        self.oc_sched_wait_std = oc_sched_wait_std
        self.number_of_values = number_of_values
        self.cpu_tier0 = -1 
        self.cpu_tier1 = -1
        self.cpu_tier2 = -1
        self.mem_tier0 = -1 
        self.mem_tier1 = -1
        self.mem_tier2 = -1
        self.cpu_state = 0
        self.mem_state = 0

    def update_state(self, cpu_state : int, mem_state : int):
        # Check cpu_state validity
        if cpu_state < 0:
            self.cpu_state = 0
        elif cpu_state > 2:
            self.cpu_state = 2
        else:
            self.cpu_state = cpu_state
        # Check mem_state validity
        if mem_state < 0:
            self.mem_state = 0
        elif mem_state > 2:
            self.mem_state = 2
        else:
            self.mem_state = mem_state

    def get_cpu_state(self):
        return self.cpu_state
    
    def get_mem_state(self):
        return self.mem_state

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

    def is_cpu_tier_defined(self):
        if self.cpu_tier0 < 0 or self.cpu_tier1 < 0 or self.cpu_tier2 < 0:
            return False
        return True

    def is_mem_tier_defined(self):
        if self.mem_tier0 < 0 or self.mem_tier1 < 0 or self.mem_tier2 < 0:
            return False
        return True

    def get_cpu_tiers(self):
        return self.cpu_tier0, self.cpu_tier1

    def get_mem_tiers(self):
        return self.mem_tier0, self.mem_tier1

    # Tiers as thresold
    def update_cpu_tiers(self, cpu_tier0, cpu_tier1):
        # Tiers are computed at the wrapper level to take into account previous slices, but updated here to be able to dump current state
        self.cpu_tier0=cpu_tier0
        self.cpu_tier1=cpu_tier1
        self.cpu_tier2=self.cpu_config

    # Tiers as thresold
    def update_mem_tiers(self, mem_tier0, mem_tier1):
        # Tiers are computed at the wrapper level to take into account previous slices, but updated here to be able to dump current state
        self.mem_tier0=mem_tier0
        self.mem_tier1=mem_tier1
        self.mem_tier2=self.mem_config

    def dump_state_to_dict(self, dump_dict : dict,  key : str, iteration : int = 0):

        if key not in dump_dict:
            dump_dict[key] = dict()

        for attribute, value in self.__dict__.items():
            if attribute not in dump_dict[key]:
                dump_dict[key][attribute] = [0 for x in range(iteration)] # in case of new vm
            dump_dict[key][attribute].append(value)

    def __str__(self):
        return "SliceVM[" +  self.cpu_avg  + "/" + self.cpu_percentile + self.cpu_config + " " +\
            self.mem_avg  + "/" + self.mem_percentile + self.mem_config + " " +\
            "cpu_state=" + str(self.cpu_state) + " mem_state=" + str(self.mem_state) + "]"