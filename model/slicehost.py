from model.sliceobject import SliceObject

class SliceHost(SliceObject):

    def __init__(self, slice_object : SliceObject):
        super().__init__(cpu_config=getattr(slice_object,'cpu_config'), mem_config=getattr(slice_object,'mem_config'), 
                cpu_percentile=getattr(slice_object,'cpu_percentile'), mem_percentile=getattr(slice_object,'mem_percentile'), 
                cpu_avg=getattr(slice_object,'cpu_avg'), mem_avg=getattr(slice_object,'mem_avg'),
                cpu_std=getattr(slice_object,'cpu_std'), mem_std=getattr(slice_object,'mem_std'), 
                oc_page_fault=getattr(slice_object,'oc_page_fault'), oc_page_fault_std=getattr(slice_object,'oc_page_fault_std'),
                oc_sched_wait=getattr(slice_object,'oc_sched_wait'), oc_sched_wait_std=getattr(slice_object,'oc_sched_wait_std'),
                cpi=getattr(slice_object,'cpi'), hwcpucycles=getattr(slice_object,'hwcpucycles'),
                number_of_values=getattr(slice_object,'number_of_values'))

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