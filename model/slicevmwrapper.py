from model.slicevm import SliceVm
import numpy as np

class SliceVmWrapper(object):

    def __init__(self, domain_name : str):
        self.domain_name=domain_name
        self.vm_seen = 0
        self.vm_last_seen = 0
        self.slice_vm_list=list()
        self.max_data = 3
        self.debug_cpu_reason = "=0 no prev data"
        self.debug_mem_reason = "=0 no prev data"

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
        cpu_std = np.std(domain_data['cpu_usage'])
        mem_std = np.std(domain_data['mem_rss'])
        # Overcommitment indicators
        oc_page_fault = np.percentile(domain_data['swpagefaults'],90)
        oc_page_fault_std=np.std(domain_data['swpagefaults'])
        oc_sched_wait = np.percentile(domain_data['sched_busy'],90)
        oc_sched_wait_std=np.std(domain_data['sched_busy'])
        slice_vm = SliceVm(cpu_config=cpu_config, mem_config=mem_config, 
                cpu_percentile=cpu_percentile, mem_percentile=mem_percentile, 
                cpu_avg=cpu_avg, mem_avg=mem_avg,
                cpu_std=cpu_std, mem_std=mem_std, 
                oc_page_fault=oc_page_fault, oc_page_fault_std=oc_page_fault_std,
                oc_sched_wait=oc_sched_wait, oc_sched_wait_std=oc_sched_wait_std)
        self.compute_state_of_new_slice(slice_vm)
        self.add_slice(slice_vm)

    def add_slice(self, slice : SliceVm):
        if self.max_data<len(self.slice_vm_list):
            self.slice_vm_list.pop(0) # remove oldest element
        self.slice_vm_list.append(slice)

    def get_slices_metric(self, metric : str):
        metric_list = list()
        for slice in self.slice_vm_list:
            metric_list.append(getattr(slice, metric))
        return metric_list

    def get_slices_coherent_value_of_metric(self, metric : str, std_metric : str, multiplier : int = 1):
        last_slice = self.get_last_slice()
        return getattr(last_slice, metric) + multiplier*getattr(last_slice, std_metric)

    def get_last_slice(self):
        return self.slice_vm_list[-1]

    def compute_cpu_state_of_new_slice(self, new_slice : SliceVm, previous_cpu_state : int):
        # If config changed
        if(self.get_slices_metric('cpu_config')[-1] != new_slice.cpu_config):
            self.debug_cpu_reason = ">0 conf changed"
            return 0
        # If oc is too important
        if(self.get_slices_coherent_value_of_metric('oc_sched_wait', 'oc_sched_wait_std') < new_slice.oc_sched_wait):
            self.debug_cpu_reason = ">0 perf oc desc"
            return 0
        # If behavior changed
        if(self.get_slices_coherent_value_of_metric('cpu_avg', 'cpu_std') < new_slice.cpu_avg):
            self.debug_cpu_reason = "-1 avg increase"
            return previous_cpu_state-1
        if(self.get_slices_coherent_value_of_metric('cpu_percentile', 'cpu_std') < new_slice.cpu_percentile):
            self.debug_cpu_reason = "-1 nth increase"
            return previous_cpu_state-1
        # Stability case
        self.debug_cpu_reason = "+1 usage stable"
        return previous_cpu_state+1

    def compute_mem_state_of_new_slice(self, new_slice : SliceVm, previous_mem_state : int):
        # If config changed
        if(self.get_slices_metric('mem_config')[-1] != new_slice.mem_config):
            self.debug_mem_reason = ">0 conf changed"
            return 0
        # If oc is too important
        if(self.get_slices_coherent_value_of_metric('oc_page_fault', 'oc_page_fault_std') < new_slice.oc_page_fault):
            self.debug_mem_reason = ">0 perf oc desc"
            return 0
        # If behavior changed
        if(self.get_slices_coherent_value_of_metric('mem_avg', 'mem_std') < new_slice.mem_avg):
            self.debug_mem_reason = "-1 avg increase"
            return previous_mem_state-1
        if(self.get_slices_coherent_value_of_metric('mem_percentile', 'mem_std') < new_slice.mem_percentile):
            self.debug_mem_reason = "-1 nth increase"
            return previous_mem_state-1
        # Stability case
        self.debug_mem_reason = "+1 usage stable"
        return previous_mem_state+1

    def compute_state_of_new_slice(self, new_slice : SliceVm):
        cpu_state = 0
        mem_state = 0
        if(self.slice_vm_list):
            cpu_state = self.compute_cpu_state_of_new_slice(new_slice, getattr(self.slice_vm_list[-1], 'cpu_state'))
            mem_state = self.compute_mem_state_of_new_slice(new_slice, getattr(self.slice_vm_list[-1], 'mem_state'))
        new_slice.update_state(cpu_state = cpu_state, mem_state = mem_state)

    def get_cpu_mem_tier(self): # return cpu_min, cpu_max, mem_min, mem_max
        last_slice = self.get_last_slice()
        cpu_min, cpu_max = last_slice.get_cpu_tier()
        mem_min, mem_max = last_slice.get_mem_tier()
        return cpu_min, cpu_max, mem_min, mem_max

    def __str__(self):
        if(len(self.slice_vm_list)>0):
            cpu_min, cpu_max, mem_min, mem_max = self.get_cpu_mem_tier()
            cpu_state = getattr(self.get_last_slice(), 'cpu_state')
            mem_state = getattr(self.get_last_slice(), 'mem_state')
            return "SliceVmWrapper for " + self.domain_name + ": " +\
                 "cpu_state=" + str(cpu_state) + "(" + self.debug_cpu_reason + ") [" + str(round(cpu_min,1)) + ";" + str(round(cpu_max,1)) + "] " +\
                 "mem_state=" + str(mem_state) + "(" + self.debug_mem_reason + ") [" + str(round(mem_min,1)) + ";" + str(round(mem_max,1)) + "]"
        else:
            return "SliceVmWrapper for " + self.domain_name + ": no data"