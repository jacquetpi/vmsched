from model.slicevm import SliceVm
import numpy as np
import math
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
        cpu_percentile = dict()
        mem_percentile = dict()
        for i in range(10, 100, 5): # percentiles from 10 to 95
            cpu_percentile[i] = np.percentile(domain_data['cpu_usage'],i)
            mem_percentile[i] = np.percentile(domain_data['mem_rss'],i)
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
        self.compute_state_of_new_slice(slice_vm)
        self.add_slice(slice_vm)

    def add_slice(self, slice : SliceVm):
        if self.is_historical_full():
            self.slice_vm_list.pop(0) # remove oldest element
        self.slice_vm_list.append(slice)

    def is_historical_full(self):
        return len(self.slice_vm_list) >= (self.historical_occurences+1) # +1 as we want to compare, let's say a day, with its previous occurence

    def get_slices_metric(self, metric : str = None, cpu_percentile : int = None, mem_percentile : int = None):
        metric_list = list()
        for slice in self.slice_vm_list:
            if metric is not None:
                metric_list.append(getattr(slice, metric))
            elif cpu_percentile is not None:
                metric_list.append(slice.get_cpu_percentile(cpu_percentile))
            elif mem_percentile is not None:
                metric_list.append(slice.get_mem_percentile(mem_percentile))
        return metric_list

    def get_slices_max_metric(self, metric : str = None, cpu_percentile : int = None, mem_percentile : int = None):
        max = None
        value = None
        for slice in self.slice_vm_list:
            if metric is not None:
                value =  getattr(slice, metric)
            elif cpu_percentile is not None:
                value =  slice.get_cpu_percentile(cpu_percentile)
            elif mem_percentile is not None:
                value =  slice.get_mem_percentile(mem_percentile)
            if (max is None) or max < value:
                max = value
        return max

    def is_incoherent_value_according_to_pvalue(self, new_slice : SliceVm, metric : str, std_metric : str):
        last_slice = self.get_last_slice()
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind_from_stats.html
        stats, pvalue = ttest_ind_from_stats(
                            getattr(last_slice, metric), getattr(last_slice, std_metric), getattr(last_slice, 'number_of_values'), 
                            getattr(new_slice, metric), getattr(new_slice, std_metric), getattr(new_slice, 'number_of_values'))
        # identical list return nan, nan which is evaluated as false
        return pvalue < 0.1

    def is_incoherent_value(self, new_slice : SliceVm, std_metric : str, metric : str = None, cpu_percentile : int = None, mem_percentile : int = None, multiplier : int = 10):
        last_slice = self.get_last_slice()
        if metric is not None:
            last_value = self.get_slices_max_metric(metric=metric)
            new_value = getattr(new_slice, metric)
        elif cpu_percentile is not None:
            last_value = self.get_slices_max_metric(cpu_percentile=cpu_percentile)
            new_value = new_slice.get_cpu_percentile(cpu_percentile)
        elif mem_percentile is not None:
            last_value = self.get_slices_max_metric(mem_percentile=mem_percentile)
            new_value = new_slice.get_mem_percentile(mem_percentile)
        else:
            raise ValueError("No metrics passed to is_incoherent_value()")
        thresold = last_value + multiplier*getattr(last_slice, std_metric)
        return new_value > thresold

    def get_last_slice(self):
        return self.slice_vm_list[-1]

    def compute_cpu_state_of_new_slice(self, new_slice : SliceVm):
        current_cpu_state = self.get_last_slice().get_cpu_state()
        # If config changed
        if (self.get_last_slice().get_cpu_config() != new_slice.cpu_config):
            self.debug_cpu_reason = ">0 conf changed"
            return 0
        # If oc is too important
        if self.is_incoherent_value(new_slice=new_slice, metric='oc_sched_wait', std_metric='oc_sched_wait_std'):
            self.debug_cpu_reason = ">0 perf oc desc"
            return 0
        # If behavior changed
        if self.is_incoherent_value(new_slice=new_slice, metric='cpu_avg', std_metric='cpu_std'):
            self.debug_cpu_reason = "-1 avg increase"
            return current_cpu_state-1
        if self.is_incoherent_value(new_slice=new_slice, cpu_percentile=90, std_metric='cpu_std'):
            self.debug_cpu_reason = "-1 nth increase"
            return current_cpu_state-1
        # Stability case
        self.debug_cpu_reason = "+1 usage stable"
        return current_cpu_state+1

    def compute_mem_state_of_new_slice(self, new_slice : SliceVm):
        current_mem_state = self.get_last_slice().get_mem_state()
        # If config changed
        if (self.get_last_slice().get_mem_config() != new_slice.mem_config):
            self.debug_mem_reason = ">0 conf changed"
            return 0
        # If oc is too important
        if self.is_incoherent_value(new_slice=new_slice, metric='oc_page_fault', std_metric='oc_page_fault_std'):
            self.debug_mem_reason = ">0 perf oc desc"
            return 0
        # If behavior changed
        if self.is_incoherent_value(new_slice=new_slice, metric='mem_avg', std_metric='mem_std'):
            self.debug_mem_reason = "-1 avg increase"
            return current_mem_state-1
        if self.is_incoherent_value(new_slice=new_slice, mem_percentile=90, std_metric='mem_std'):
            self.debug_mem_reason = "-1 nth increase"
            return current_mem_state-1
        # Stability case
        self.debug_mem_reason = "+1 usage stable"
        return current_mem_state+1

    def compute_state_of_new_slice(self, new_slice : SliceVm):
        cpu_state = 0
        mem_state = 0
        if(self.is_historical_full()):
            cpu_state = self.compute_cpu_state_of_new_slice(new_slice)
            mem_state = self.compute_mem_state_of_new_slice(new_slice)
        new_slice.update_state(cpu_state = cpu_state, mem_state = mem_state)

    # VM tiers as thresold
    def get_cpu_tiers(self): # return tier0, tier1
        cpu_state = self.get_last_slice().get_cpu_state()
        if cpu_state == 0:
            cpu_tier0 = self.get_last_slice().get_cpu_config()
            cpu_tier1 = self.get_last_slice().get_cpu_config()
        elif cpu_state == 1:
            cpu_tier0 = math.ceil(self.get_slices_max_metric(cpu_percentile=90))
            cpu_tier1 = self.get_last_slice().get_cpu_config()
        else:
            cpu_tier0 = math.ceil(self.get_slices_max_metric(metric='cpu_avg'))
            cpu_tier1 = math.ceil(self.get_slices_max_metric(cpu_percentile=90))
        self.get_last_slice().update_cpu_tiers(cpu_tier0, cpu_tier1)
        return cpu_tier0, cpu_tier1

    # VM tiers as thresold
    def get_mem_tiers(self): # return tier0, tier1
        mem_state = self.get_last_slice().get_mem_state()
        if mem_state == 0:
            mem_tier0 = self.get_last_slice().get_mem_config()
            mem_tier1 = self.get_last_slice().get_mem_config()
        elif mem_state == 1:
            mem_tier0 = math.ceil(self.get_slices_max_metric(mem_percentile=90))
            mem_tier1 = self.get_last_slice().get_mem_config()
        else:
            mem_tier0 = math.ceil(self.get_slices_max_metric(metric='mem_avg'))
            mem_tier1 = math.ceil(self.get_slices_max_metric(mem_percentile=90))
        self.get_last_slice().update_mem_tiers(mem_tier0, mem_tier1)
        return mem_tier0, mem_tier1

    def get_cpu_mem_tiers(self): # return cpu_tier0, cpu_tier1, mem_tier0, mem_tier1
        last_slice = self.get_last_slice()
        cpu_tier0, cpu_tier1 = self.get_cpu_tiers()
        mem_tier0, mem_tier1 = self.get_mem_tiers()
        return cpu_tier0, cpu_tier1, mem_tier0, mem_tier1

    def __str__(self):
        if(len(self.slice_vm_list)>0):
            cpu_tier0, cpu_tier1, mem_tier0, mem_tier1 = self.get_cpu_mem_tiers()
            cpu_state = self.get_last_slice().get_cpu_state()
            mem_state = self.get_last_slice().get_mem_state()
            return "SliceVmWrapper for " + self.domain_name + ": " +\
                 "cpu_state=" + str(cpu_state) + "(" + self.debug_cpu_reason + ") [" + str(round(cpu_tier0,1)) + ";" + str(round(cpu_tier1,1)) + "] " +\
                 "mem_state=" + str(mem_state) + "(" + self.debug_mem_reason + ") [" + str(round(mem_tier0,1)) + ";" + str(round(mem_tier1,1)) + "]"
        else:
            return "SliceVmWrapper for " + self.domain_name + ": no data"