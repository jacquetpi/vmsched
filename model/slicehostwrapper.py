from model.sliceobjectwrapper import SliceObjectWrapper
from model.sliceobject import SliceObject
from model.slicehost import SliceHost
import numpy as np

class SliceHostWrapper(SliceObjectWrapper):

    def __init__(self, host_name : str, historical_occurences : int):
        super().__init__(historical_occurences)
        self.host_name=host_name

    def add_slice_data_from_raw(self, host_data : dict):
        if(len(host_data.keys()) == 0):
            print("Empty data on slice encountered on host " + self.host_name)
            return
        slice_host = SliceHost(slice_object=self.get_slice_object_from_raw(host_data),
                        vm_list=host_data["vm"])
        self.add_slice(slice_host)

    def add_slice_data_from_dump(self, host_dump_data : dict, occurence : int):
        if(len(host_dump_data.keys()) == 0):
            print("Empty data on slice encountered on dump " + self.host_name)
            return
        slice_host = SliceHost(slice_object=self.get_slice_object_from_dump(dump_data=host_dump_data, occurence=occurence, epoch=host_dump_data["epoch"][occurence]),
                        vm_list=host_dump_data["vm_list"])
        self.add_slice(slice_host)

    def get_host_config(self):
        cpu_config_list = self.get_slices_metric("cpu_config")
        mem_config_list = self.get_slices_metric("cpu_config")
        if cpu_config_list:
            cpu_config = self.get_slices_metric("cpu_config")[-1]
        else:
            cpu_config=-1
        if mem_config_list:
            mem_config = self.get_slices_metric("mem_config")[-1]
        else:
            mem_config=-1
        return cpu_config, mem_config

    def get_host_average(self):
        cpu_usage_list = self.get_slices_metric("cpu_avg")
        mem_usage_list = self.get_slices_metric("mem_avg")
        return np.average(cpu_usage_list), np.average(mem_usage_list)

    def get_host_percentile(self):
        cpu_usage_list = self.get_slices_metric(cpu_percentile=90)
        mem_usage_list = self.get_slices_metric(mem_percentile=90)
        return np.max(cpu_usage_list), np.max(mem_usage_list)

    def is_stable(self): # Host is considered stable if no new VM were deployed
        if not self.is_historical_full():
            return False
        # VM name is supposed unique
        for vm in self.get_last_slice().get_vm_list():
            if not self.get_oldest_slice().is_vm_in(vm):
                return False
        return True

    # Host tiers as threshold
    def get_cpu_tiers(self): # return tier0, tier1
        if self.is_stable():
            cpu_tier0 = self.round_to_upper_nearest(x=self.get_slices_max_metric(cpu_percentile=95), nearest_val=0.50) # unity is vcpu
            cpu_tier1 = self.round_to_upper_nearest(x=self.get_slices_max_metric(cpu_percentile=95), nearest_val=0.50) # unity is vcpu
        # TODO : is last obtained by this way? Is it the right way?
        elif self.get_last_slice().is_cpu_tier_defined():
            cpu_tier0 = 1
            cpu_tier1 = 1
            # TODO
        else:
            # No OC
            cpu_tier0 = 1
            cpu_tier1 = 1
            # TODO
        self.get_last_slice().update_cpu_tiers(cpu_tier0, cpu_tier1)
        return cpu_tier0, cpu_tier1

    def get_cpu_mem_tiers(self): # return cpu_tier0, cpu_tier1, mem_tier0, mem_tier1
        last_slice = self.get_last_slice()
        cpu_tier0, cpu_tier1 = self.get_cpu_tiers()
        mem_tier0, mem_tier1 = self.get_mem_tiers()
        return cpu_tier0, cpu_tier1, mem_tier0, mem_tier1

    def __str__(self):
        if(len(self.slice_object_list)>0):
            cpu_config, mem_config = self.get_host_config()
            cpu_avg, mem_avg = self.get_host_average()
            cpu_percentile, mem_percentile = self.get_host_percentile()
            return "SliceHostWrapper for " + self.host_name + " hostcpu avg/percentile/config " +\
                str(round(cpu_avg,1)) + "/" + str(round(cpu_percentile,1)) + "/" + str(int(cpu_config)) + " mem avg/percentile/config " +\
                str(round(mem_avg,1)) + "/" + str(round(mem_percentile,1)) + "/" + str(int(mem_config))
        else:
            return "SliceHostWrapper for " + self.host_name + ": no data"