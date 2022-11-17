from model.sliceobject import SliceObject

class SliceVm(SliceObject):

    def __init__(self, slice_object : SliceObject):
        super().__init__(cpu_config=getattr(slice_object,'cpu_config'), mem_config=getattr(slice_object,'mem_config'), 
                cpu_percentile=getattr(slice_object,'cpu_percentile'), mem_percentile=getattr(slice_object,'mem_percentile'), 
                cpu_avg=getattr(slice_object,'cpu_avg'), mem_avg=getattr(slice_object,'mem_avg'),
                cpu_std=getattr(slice_object,'cpu_std'), mem_std=getattr(slice_object,'mem_std'),
                cpu_max=getattr(slice_object,'cpu_max'), mem_max=getattr(slice_object,'mem_max'),
                oc_page_fault=getattr(slice_object,'oc_page_fault'), oc_page_fault_std=getattr(slice_object,'oc_page_fault_std'),
                oc_sched_wait=getattr(slice_object,'oc_sched_wait'), oc_sched_wait_std=getattr(slice_object,'oc_sched_wait_std'),
                cpi=getattr(slice_object,'cpi'), hwcpucycles=getattr(slice_object,'hwcpucycles'),
                number_of_values=getattr(slice_object,'number_of_values'))
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

    # Tiers as threshold
    def update_cpu_tiers(self, cpu_tier0, cpu_tier1):
        # Tiers are computed at the wrapper level to take into account previous slices, but updated here to be able to dump current state
        self.cpu_tier0=cpu_tier0
        self.cpu_tier1=cpu_tier1
        self.cpu_tier2=self.cpu_config

    # Tiers as threshold
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
        return "SliceVM[" +  str(self.cpu_avg)  + "/" + str(round(self.get_cpu_percentile(90))) + "/" + str(self.cpu_config) + " " +\
            str(self.mem_avg)  + "/" + str(round(self.get_mem_percentile(90)))  + "/" + str(self.mem_config) + " " +\
            "cpu_state=" + str(self.cpu_state) + " mem_state=" + str(self.mem_state) + "]"