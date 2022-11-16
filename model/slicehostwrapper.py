from model.slicehost import SliceHost
import numpy as np

class SliceHostWrapper(object):

    def __init__(self, host_name : str, historical_occurences : int):
        self.host_name=host_name
        self.host_seen = 0
        self.host_last_seen = 0
        self.slice_host_list=list()
        self.historical_occurences=historical_occurences

    def add_slice_data_from_raw(self, host_data : dict):
        if(len(host_data.keys()) == 0):
            print("Empty data on slice encountered on host " + self.host_name)
            return
        # Update wrapper metrics
        self.host_seen+=1
        self.host_last_seen = host_data['time'][-1]
        # CPU/mem indicators
        cpu_config = host_data['cpu'][-1]
        mem_config = host_data['mem'][-1]
        cpu_percentile = np.percentile(host_data['cpu_usage'],95)
        mem_percentile = np.percentile(host_data['mem_usage'],95)
        cpu_avg = np.average(host_data['cpu_usage'])
        mem_avg = np.average(host_data['mem_usage'])
        # Overcommitment indicators
        oc_page_fault = np.percentile(host_data['swpagefaults'],95)
        oc_sched_wait = np.percentile(host_data['sched_busy'],95)
        slice_host = SliceHost(cpu_config=cpu_config, mem_config=mem_config, 
                cpu_percentile=cpu_percentile, mem_percentile=mem_percentile, 
                cpu_avg=cpu_avg, mem_avg=mem_avg, 
                oc_page_fault=oc_page_fault, oc_sched_wait=oc_sched_wait)
        self.add_slice(slice_host)

    def add_slice_data_from_dump(self, host_dump_data : dict, occurence : int):
        if(len(host_dump_data.keys()) == 0):
            print("Empty data on slice encountered on dump " + self.host_name)
            return
        # Update wrapper metrics
        self.host_seen+=1
        self.host_last_seen = host_dump_data["epoch"][occurence]
        slice_host = SliceHost(cpu_config=host_dump_data["cpu_config"][occurence], mem_config=host_dump_data["mem_config"][occurence], 
                cpu_percentile=host_dump_data["cpu_percentile"][occurence], mem_percentile=host_dump_data["mem_percentile"][occurence], 
                cpu_avg=host_dump_data["cpu_avg"][occurence], mem_avg=host_dump_data["mem_avg"][occurence], 
                oc_page_fault=host_dump_data["oc_page_fault"][occurence], oc_sched_wait=host_dump_data["oc_sched_wait"][occurence])
        self.add_slice(slice_host)

    def add_slice(self, slice : SliceHost):
        if self.is_historical_full():
            self.slice_host_list.pop(0) # remove oldest element
        self.slice_host_list.append(slice)

    def is_historical_full(self):
        return len(self.slice_host_list) >= (self.historical_occurences+1) # +1 as we want to compare, let's say a slice in a day, with its previous occurence

    def get_last_slice(self):
        return self.slice_host_list[-1]
    
    def get_slice_metric(self, metric : str):
        metric_list = list()
        for slice in self.slice_host_list:
            metric_list.append(getattr(slice, metric))
        return metric_list

    def get_host_config(self):
        cpu_config_list =  self.get_slice_metric("cpu_config")
        mem_config_list =  self.get_slice_metric("cpu_config")
        if cpu_config_list:
            cpu_config = self.get_slice_metric("cpu_config")[-1]
        else:
            cpu_config=-1
        if mem_config_list:
            mem_config = self.get_slice_metric("mem_config")[-1]
        else:
            mem_config=-1
        return cpu_config, mem_config

    def get_host_average(self):
        cpu_usage_list = self.get_slice_metric("cpu_avg")
        mem_usage_list = self.get_slice_metric("mem_avg")
        return np.average(cpu_usage_list), np.average(mem_usage_list)

    def get_host_percentile(self):
        cpu_usage_list = self.get_slice_metric("cpu_percentile")
        mem_usage_list = self.get_slice_metric("mem_percentile")
        return np.max(cpu_usage_list), np.max(mem_usage_list)

    def __str__(self):
        if(len(self.slice_host_list)>0):
            cpu_config, mem_config = self.get_host_config()
            cpu_avg, mem_avg = self.get_host_average()
            cpu_percentile, mem_percentile = self.get_host_percentile()
            return "SliceHostWrapper for " + self.host_name + " hostcpu avg/percentile/config " +\
                str(round(cpu_avg,1)) + "/" + str(round(cpu_percentile,1)) + "/" + str(int(cpu_config)) + " mem avg/percentile/config " +\
                str(round(mem_avg,1)) + "/" + str(round(mem_percentile,1)) + "/" + str(int(mem_config))
        else:
            return "SliceHostWrapper for " + self.host_name + ": no data"