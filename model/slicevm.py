class SliceVm(object):

    def __init__(self, cpu_config : int, mem_config : int, 
                cpu_percentile : int, mem_percentile : int, 
                cpu_avg : int, mem_avg : int, 
                cpu_std : int, mem_std : int, 
                oc_page_fault : int, oc_page_fault_std : int,
                oc_sched_wait : int, oc_sched_wait_std : int,
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

    def get_cpu_tier(self):
        if self.cpu_state == 0:
            cpu_min = self.cpu_config
            cpu_max = self.cpu_config
        elif self.cpu_state == 1:
            cpu_min = self.cpu_percentile
            cpu_max = self.cpu_config
        else:
            cpu_min = self.cpu_avg
            cpu_max = self.cpu_percentile
        return cpu_min, cpu_max

    def get_mem_tier(self):
        if self.mem_state == 0:
            mem_min = self.mem_config
            mem_max = self.mem_config
        elif self.mem_state == 1:
            mem_min = self.mem_percentile
            mem_max = self.mem_config
        else:
            mem_min = self.mem_avg
            mem_max = self.mem_percentile
        return mem_min, mem_max

    def dump_state_to_dict(self, dump_dict : dict,  key : str, iteration : int = 0):
        if key not in dump_dict:
            dump_dict[key] = dict()
            dump_dict[key]["cpu_config"] = [0 for x in range(iteration)] # in case of new vm 
            dump_dict[key]["cpu_avg"] = [0 for x in range(iteration)] 
            dump_dict[key]["cpu_percentile"] = [0 for x in range(iteration)] 
            dump_dict[key]["cpu_std"] = [0 for x in range(iteration)] 
            dump_dict[key]["cpu_tier0"] = [0 for x in range(iteration)] 
            dump_dict[key]["cpu_tier1"] = [0 for x in range(iteration)] 
            dump_dict[key]["cpu_state"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_config"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_avg"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_std"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_percentile"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_tier0"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_tier1"] = [0 for x in range(iteration)] 
            dump_dict[key]["mem_state"] = [0 for x in range(iteration)] 
            dump_dict[key]["oc_page_fault"] = [0 for x in range(iteration)] 
            dump_dict[key]["oc_page_fault_std"] = [0 for x in range(iteration)] 
            dump_dict[key]["oc_sched_wait"] = [0 for x in range(iteration)] 
            dump_dict[key]["oc_sched_wait_std"] = [0 for x in range(iteration)] 
        dump_dict[key]["cpu_config"].append(self.cpu_config)
        dump_dict[key]["cpu_avg"].append(self.cpu_avg)
        dump_dict[key]["cpu_percentile"].append(self.cpu_percentile)
        dump_dict[key]["cpu_std"].append(self.cpu_std)
        cpu_tier0, cpu_tier1 = self.get_cpu_tier()
        cpu_tier1 = cpu_tier1 - cpu_tier0
        if cpu_tier1<0:
            cpu_tier1=0
        dump_dict[key]["cpu_tier0"].append(cpu_tier0)
        dump_dict[key]["cpu_tier1"].append(cpu_tier1)
        dump_dict[key]["cpu_state"].append(self.cpu_state)
        dump_dict[key]["mem_config"].append(self.mem_config)
        dump_dict[key]["mem_avg"].append(self.mem_avg)
        dump_dict[key]["mem_std"].append(self.mem_std)
        dump_dict[key]["mem_percentile"].append(self.mem_percentile)
        mem_tier0, mem_tier1 = self.get_mem_tier()
        mem_tier1 = mem_tier1 - mem_tier0
        if mem_tier1<0:
            mem_tier1=0
        dump_dict[key]["mem_tier0"].append(mem_tier0)
        dump_dict[key]["mem_tier1"].append(mem_tier1)
        dump_dict[key]["mem_state"].append(self.mem_state)
        dump_dict[key]["oc_page_fault"].append(self.oc_page_fault)
        dump_dict[key]["oc_page_fault_std"].append(self.oc_page_fault_std)
        dump_dict[key]["oc_sched_wait"].append(self.oc_sched_wait)
        dump_dict[key]["oc_sched_wait_std"].append(self.oc_sched_wait_std)

    def __str__(self):
        return "SliceVM[" +  self.cpu_avg  + "/" + self.cpu_percentile + self.cpu_config + " " +\
            self.mem_avg  + "/" + self.mem_percentile + self.mem_config + " " +\
            "cpu_state=" + str(self.cpu_state) + " mem_state=" + str(self.mem_state) + "]"