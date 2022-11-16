from model.sliceobject import SliceObject
import numpy as np
import math

class SliceObjectWrapper(object):

    def __init__(self, historical_occurences : int):
        self.historical_occurences=historical_occurences
        self.object_seen = 0
        self.object_last_seen = 0
        self.slice_object_list=list()

    def get_slice_object_from_raw(self, data : dict):
        if "mem_rss" in data:
            memory_metric = "mem_rss" # VM case
        else:
            memory_metric = "mem_usage" # host case
        # Update wrapper metrics
        self.object_seen+=1
        self.object_last_seen = int(data['time'][-1])
        # CPU/mem indicators
        cpu_config = data['cpu'][-1]
        mem_config = data['mem'][-1]
        cpu_percentile = dict()
        mem_percentile = dict()
        for i in range(10, 100, 5): # percentiles from 10 to 95
            cpu_percentile[i] = np.percentile(data['cpu_usage'],i)
            mem_percentile[i] = np.percentile(data[memory_metric],i)
        cpu_avg = np.average(data['cpu_usage'])
        mem_avg = np.average(data[memory_metric])
        cpu_std = np.std(data['cpu_usage'])
        mem_std = np.std(data[memory_metric])
        # Overcommitment indicators
        oc_page_fault = np.percentile(data['swpagefaults'],90)
        oc_page_fault_std=np.std(data['swpagefaults'])
        oc_sched_wait = np.percentile(data['sched_busy'],90)
        oc_sched_wait_std=np.std(data['sched_busy'])
        cpi = dict()
        hwcpucycles = dict()
        if "cpi" in data:
            for i in range(10, 100, 5):
                cpi[i] = np.percentile(data["cpi"],i)
        if "hwcpucycles" in data:
            for i in range(10, 100, 5):
                hwcpucycles[i] = np.percentile(data["hwcpucycles"],i)
        sliceObject = SliceObject(cpu_config=cpu_config, mem_config=mem_config, 
                cpu_percentile=cpu_percentile, mem_percentile=mem_percentile, 
                cpu_avg=cpu_avg, mem_avg=mem_avg,
                cpu_std=cpu_std, mem_std=mem_std, 
                oc_page_fault=oc_page_fault, oc_page_fault_std=oc_page_fault_std,
                oc_sched_wait=oc_sched_wait, oc_sched_wait_std=oc_sched_wait_std,
                cpi=cpi, hwcpucycles=hwcpucycles,
                number_of_values=len(data['time']))
        return sliceObject

    def get_slice_object_from_dump(self, dump_data : dict, occurence : int, epoch : int):
        # Update wrapper metrics
        self.object_seen+=1
        self.object_last_seen = epoch
        sliceObject = SliceObject(cpu_config=dump_data["cpu_config"][occurence], mem_config=dump_data["mem_config"][occurence], 
                cpu_percentile=dump_data["cpu_percentile"][occurence], mem_percentile=dump_data["mem_percentile"][occurence],
                cpu_avg=dump_data["cpu_avg"][occurence], mem_avg=dump_data["mem_avg"][occurence],
                cpu_std=dump_data["cpu_std"][occurence], mem_std=dump_data["mem_std"][occurence], 
                oc_page_fault=dump_data["oc_page_fault"][occurence], oc_page_fault_std=dump_data["oc_page_fault_std"][occurence],
                oc_sched_wait=dump_data["oc_sched_wait"][occurence], oc_sched_wait_std=dump_data["oc_sched_wait_std"][occurence],
                cpi=dump_data["cpi"][occurence], hwcpucycles=dump_data["hwcpucycles"][occurence],
                number_of_values=dump_data["number_of_values"][occurence])
        return sliceObject

    def add_slice(self, slice : SliceObject):
        if self.is_historical_full():
            self.slice_object_list.pop(0) # remove oldest element
        self.slice_object_list.append(slice)

    def is_historical_full(self):
        return len(self.slice_object_list) >= (self.historical_occurences+1) # +1 as we want to compare, let's say a slice in a day, with its previous occurence

    def get_slices_metric(self, metric : str = None, cpu_percentile : int = None, mem_percentile : int = None, cpi_percentile : int = None, hwcpucycles_percentile : int = None):
        metric_list = list()
        for slice in self.slice_object_list:
            if metric is not None:
                metric_list.append(getattr(slice, metric))
            elif cpu_percentile is not None:
                metric_list.append(slice.get_cpu_percentile(cpu_percentile))
            elif mem_percentile is not None:
                metric_list.append(slice.get_mem_percentile(mem_percentile))
            elif cpi_percentile is not None:
                metric_list.append(slice.get_cpi_percentile(cpi_percentile))
            elif hwcpucycles_percentile is not None:
                metric_list.append(slice.get_hwcpucycles_percentile(hwcpucycles_percentile))
        return metric_list

    def get_slices_max_metric(self, metric : str = None, cpu_percentile : int = None, mem_percentile : int = None, cpi_percentile : int = None, hwcpucycles_percentile : int = None):
        max = None
        value = None
        for slice in self.slice_object_list:
            if metric is not None:
                value =  getattr(slice, metric)
            elif cpu_percentile is not None:
                value =  slice.get_cpu_percentile(cpu_percentile)
            elif mem_percentile is not None:
                value =  slice.get_mem_percentile(mem_percentile)
            elif cpi_percentile is not None:
                value =  slice.get_cpi_percentile(cpi_percentile)
            elif hwcpucycles_percentile is not None:
                value = slice.get_hwcpucycles_percentile(hwcpucycles_percentile)
            if (max is None) or max < value:
                max = value
        return max

    def get_last_slice(self):
        return self.slice_object_list[-1]

    def round_to_upper_nearest(self, x : int, nearest_val : int):
        return nearest_val * math.ceil(x/nearest_val)