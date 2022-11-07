from model.slicevm import SliceVm
import numpy as np
from scipy.stats import ttest_ind_from_stats

class SliceVmWrapper(object):

    def __init__(self, domain_name : str, historical_occurences : int):
        self.domain_name=domain_name
        self.historical_occurences=historical_occurences
        self.vm_seen = 0
        self.vm_last_seen = 0
        self.slice_vm_list=list()
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
                oc_sched_wait=oc_sched_wait, oc_sched_wait_std=oc_sched_wait_std,
                number_of_values=len(domain_data['time']))
        print(domain_data['time'])
        self.compute_state_of_new_slice(slice_vm)
        self.add_slice(slice_vm)

    def add_slice(self, slice : SliceVm):
        if self.historical_occurences<len(self.slice_vm_list):
            self.slice_vm_list.pop(0) # remove oldest element
        self.slice_vm_list.append(slice)

    def get_slices_metric(self, metric : str):
        metric_list = list()
        for slice in self.slice_vm_list:
            metric_list.append(getattr(slice, metric))
        return metric_list

    def is_incoherent_value(self, new_slice : SliceVm, metric : str, std_metric : str):
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind_from_stats.html 
        # scipy.stats.ttest_ind_from_stats
        last_slice = self.get_last_slice()
        stats, pvalue = ttest_ind_from_stats(
                            getattr(last_slice, metric), getattr(last_slice, std_metric), getattr(last_slice, 'number_of_values'), 
                            getattr(new_slice, metric), getattr(new_slice, std_metric), getattr(new_slice, 'number_of_values'))
        # identical list return nan, nan which is evaluated as false
        return pvalue < 0.1

    def get_last_slice(self):
        return self.slice_vm_list[-1]

    def compute_cpu_state_of_new_slice(self, new_slice : SliceVm):
        current_cpu_state = getattr(self.get_last_slice(), 'cpu_state')
        # If config changed
        if (self.get_slices_metric('cpu_config')[-1] != new_slice.cpu_config):
            self.debug_cpu_reason = ">0 conf changed"
            return 0
        # If oc is too important
        if self.is_incoherent_value(new_slice, 'oc_sched_wait', 'oc_sched_wait_std'):
            self.debug_cpu_reason = ">0 perf oc desc"
            return 0
        # If behavior changed
        if self.is_incoherent_value(new_slice, 'cpu_avg', 'cpu_std'):
            self.debug_cpu_reason = "-1 avg increase"
            return current_cpu_state-1
        if self.is_incoherent_value(new_slice, 'cpu_percentile', 'cpu_std'):
            self.debug_cpu_reason = "-1 nth increase"
            return current_cpu_state-1
        # Stability case
        self.debug_cpu_reason = "+1 usage stable"
        return current_cpu_state+1

    def compute_mem_state_of_new_slice(self, new_slice : SliceVm):
        current_mem_state = getattr(self.get_last_slice(), 'mem_state')
        # If config changed
        if (self.get_slices_metric('mem_config')[-1] != new_slice.mem_config):
            self.debug_mem_reason = ">0 conf changed"
            return 0
        # If oc is too important
        if self.is_incoherent_value(new_slice, 'oc_page_fault', 'oc_page_fault_std'):
            self.debug_mem_reason = ">0 perf oc desc"
            return 0
        # If behavior changed
        if self.is_incoherent_value(new_slice, 'mem_avg', 'mem_std'):
            self.debug_mem_reason = "-1 avg increase"
            return current_mem_state-1
        if self.is_incoherent_value(new_slice, 'mem_percentile', 'mem_std'):
            self.debug_mem_reason = "-1 nth increase"
            return current_mem_state-1
        # Stability case
        self.debug_mem_reason = "+1 usage stable"
        return current_mem_state+1

    def compute_state_of_new_slice(self, new_slice : SliceVm):
        cpu_state = 0
        mem_state = 0
        if(self.slice_vm_list):
            cpu_state = self.compute_cpu_state_of_new_slice(new_slice)
            mem_state = self.compute_mem_state_of_new_slice(new_slice)
        new_slice.update_state(cpu_state = cpu_state, mem_state = mem_state)

    def get_cpu_tiers_thresold_from_state(self, cpu_state : int):
        if cpu_state == 0:
            cpu_min = self.get_last_slice().get_cpu_config()
            cpu_max = self.get_last_slice().get_cpu_config()
        elif cpu_state == 1:
            cpu_min = np.max(self.get_slices_metric('cpu_percentile'))
            cpu_max = self.get_last_slice().get_cpu_config()
        else:
            cpu_min = np.max(self.get_slices_metric('cpu_avg'))
            cpu_max = np.max(self.get_slices_metric('cpu_percentile'))
        return cpu_min, cpu_max

    def get_mem_tiers_thresold_from_state(self, mem_state : int):
        if mem_state == 0:
            mem_min = self.get_last_slice().get_mem_config()
            mem_max = self.get_last_slice().get_mem_config()
        elif mem_state == 1:
            mem_min = np.max(self.get_slices_metric('mem_percentile'))
            mem_max = self.get_last_slice().get_mem_config()
        else:
            mem_min = np.max(self.get_slices_metric('mem_avg'))
            mem_max = np.max(self.get_slices_metric('mem_percentile'))
        return mem_min, mem_max


    def get_cpu_mem_tier(self): # return cpu_min, cpu_max, mem_min, mem_max
        last_slice = self.get_last_slice()
        cpu_min, cpu_max = self.get_cpu_tiers_thresold_from_state(last_slice.get_cpu_state())
        mem_min, mem_max = self.get_mem_tiers_thresold_from_state(last_slice.get_mem_state())
        return cpu_min, cpu_max, mem_min, mem_max

    def __str__(self):
        if(len(self.slice_vm_list)>0):
            cpu_min, cpu_max, mem_min, mem_max = self.get_cpu_mem_tier()
            cpu_state = self.get_last_slice().get_cpu_state()
            mem_state = self.get_last_slice().get_mem_state()
            return "SliceVmWrapper for " + self.domain_name + ": " +\
                 "cpu_state=" + str(cpu_state) + "(" + self.debug_cpu_reason + ") [" + str(round(cpu_min,1)) + ";" + str(round(cpu_max,1)) + "] " +\
                 "mem_state=" + str(mem_state) + "(" + self.debug_mem_reason + ") [" + str(round(mem_min,1)) + ";" + str(round(mem_max,1)) + "]"
        else:
            return "SliceVmWrapper for " + self.domain_name + ": no data"