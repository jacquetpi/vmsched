class SliceHost(object):

    def __init__(self, cpu_config : int, mem_config : int, 
                cpu_percentile : int, mem_percentile : int, 
                cpu_avg : int, mem_avg : int, 
                oc_page_fault : int, oc_sched_wait : int):
        self.cpu_config = cpu_config
        self.mem_config = mem_config
        self.cpu_percentile = cpu_percentile
        self.mem_percentile = mem_percentile
        self.cpu_avg = cpu_avg
        self.mem_avg = mem_avg
        self.oc_page_fault = oc_page_fault
        self.oc_sched_wait = oc_sched_wait

    def __str__(self):
        return "SliceHost[" +  str(round(self.cpu_avg,1))  + "/" + str(round(self.cpu_percentile,1)) + "/" + str(int(self.cpu_config)) + " " +\
            str(round(self.mem_avg,1))  + "/" + str(round(self.mem_percentile,1)) + "/" + str(int(self.mem_config)) + " " +\
            "alert_oc_cpu=" + str(self.alert_oc_cpu()) + " alert_oc_mem=" + str(self.alert_oc_mem()) + "]"

    def alert_oc_cpu(self):
        return (self.oc_sched_wait>1000); # TODO value

    def alert_oc_mem(self):
        return (self.oc_page_fault>100000); # TODO value