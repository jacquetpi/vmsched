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
        return self.cpu_percentile[percentile]

    def get_mem_percentile(self, percentile : int):
        return self.mem_percentile[percentile]

    def dump_state_to_dict(self, dump_dict : dict,  key : str, iteration : int = 0):

        if key not in dump_dict:
            dump_dict[key] = dict()
            dump_dict[key]["cpu_tier0"]=list()
            dump_dict[key]["cpu_tier1"]=list()
            dump_dict[key]["cpu_tier2"]=list()
            dump_dict[key]["mem_tier0"]=list()
            dump_dict[key]["mem_tier1"]=list()
            dump_dict[key]["mem_tier2"]=list()

        for attribute, value in self.__dict__.items():
            if attribute not in dump_dict[key]:
                dump_dict[key][attribute] = [0 for x in range(iteration)] # in case of new vm
            dump_dict[key][attribute].append(value)

    def __str__(self):
        return "SliceVM[" +  self.cpu_avg  + "/" + self.cpu_percentile + self.cpu_config + " " +\
            self.mem_avg  + "/" + self.mem_percentile + self.mem_config + " " +\
            "cpu_state=" + str(self.cpu_state) + " mem_state=" + str(self.mem_state) + "]"