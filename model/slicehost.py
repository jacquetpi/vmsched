from model.sliceobject import SliceObject

class SliceHost(SliceObject):

    def __init__(self, slice_object : SliceObject, vm_list : list):
        # Retrieve parent attribute for computation
        slice_attributes = slice_object.__dict__
        slice_attributes["compute"] = True
        super().__init__(**slice_attributes)
        # Specific attributes
        self.vm_list=vm_list
        print(len(self.vm_list))

    def get_vm_list(self):
        return self.vm_list

    def is_vm_in(self, vm : str):
        return (vm in self.vm_list)

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
                if attribute in ["raw_data", "cpu_percentile", "mem_percentile", "cpi", "hwcpucycles"]:
                    dump_dict[attribute] = [dict() for x in range(iteration)] # in case of new host
                elif attribute in ["vm_list"]:
                    dump_dict[attribute] = [list() for x in range(iteration)]
                else:
                     dump_dict[attribute] = [0 for x in range(iteration)]
            dump_dict[attribute].append(value)