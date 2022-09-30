from slicevm import SliceVm
import numpy as np

class SliceVmWrapper(object):

    def __init__(self, domain_name : str):
        self.domain_name=domain_name
        self.vm_seen = 0
        self.vm_last_seen = 0
        self.slice_vm_list=list()
        self.max_data = 3

    def add_data(self, domain_data : dict):
        if(len(domain_data.keys()) == 0):
            print("Empty data on slice encountered on domain " + self.domain_name)
            return
        # Update wrapper metrics
        self.last_seen = int(domain_data['time'][-1])
        self.vm_last_seen+=1
        # CPU/mem indicators
        cpu_config = domain_data['cpu'][-1]
        mem_config = domain_data['mem'][-1]
        cpu_percentile = np.percentile(domain_data['cpu_usage'],90)
        mem_percentile = np.percentile(domain_data['mem_rss'],90)
        cpu_avg = np.average(domain_data['cpu_usage'])
        mem_avg = np.average(domain_data['mem_rss'])
        # Overcommitment indicators
        oc_page_fault = np.percentile(domain_data['swpagefaults'],95)
        oc_sched_wait = np.percentile(domain_data['sched_busy'],95)
        slice_vm = SliceVm(cpu_config=cpu_config, mem_config=mem_config, 
                cpu_percentile=cpu_percentile, mem_percentile=mem_percentile, 
                cpu_avg=cpu_avg, mem_avg=mem_avg, 
                oc_page_fault=oc_page_fault, oc_sched_wait=oc_sched_wait)
        self.add_slice(slice_vm)

    def add_slice(self, slice : SliceVm):
        if self.max_data<len(self.slice_vm_list):
            self.slice_vm_list.pop(0) # remove oldest element
        self.slice_vm_list.append(slice)

    def get_slice_metric(self, metric : str):
        metric_list = list()
        for slice in self.slice_vm_list:
            metric_list.append(getattr(slice, metric))
        return metric_list

    def compute_lifetime_indicator(self):
        if self.vm_last_seen <= 1:
            return 0
        elif self.vm_last_seen <= 2:
            return 1
        else:
            return 2

    def get_cpu_mem_tier(self): # return cpu_min, cpu_max, mem_min, mem_max
        lifetime = self.compute_lifetime_indicator()
        if lifetime == 0: # Between t0 and t1 : we garantee the booked ressources to the VM
            cpu_max, mem_max = self.get_slice_metric('cpu_config')[-1], self.get_slice_metric('mem_config')[-1]
            cpu_min, mem_min = cpu_max, mem_max
        elif lifetime == 1: # Between t1 and t2 : we garantee the percentile to the VM and keep the booked ressources in flex space
            cpu_max, mem_max = self.get_slice_metric('cpu_config')[-1], self.get_slice_metric('mem_config')[-1]
            cpu_min, mem_min = np.max(self.get_slice_metric('cpu_percentile')), np.max(self.get_slice_metric('mem_percentile'))
        else: # From t2 : we use the average and percentile value only
            cpu_max, mem_max = np.max(self.get_slice_metric('cpu_percentile')), np.max(self.get_slice_metric('mem_percentile'))
            cpu_min, mem_min = np.max(self.get_slice_metric('cpu_avg')), np.max(self.get_slice_metric('mem_avg'))
        return cpu_min, cpu_max, mem_min, mem_max

    def __str__(self):
        if(len(self.slice_vm_list)>0):
            cpu_min, cpu_max, mem_min, mem_max = self.get_cpu_mem_tier()
            return "SliceVmWrapper for " + self.domain_name + " lifetime=" + str(self.compute_lifetime_indicator()) + " : cpu [" + str(round(cpu_min,1)) + ";" + str(round(cpu_max,1)) + "] mem [" + str(round(mem_min,1)) + ";" + str(round(mem_max,1)) + "]"
        else:
            return "SliceVmWrapper for " + self.domain_name + ": no data"