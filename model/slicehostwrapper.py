from model.sliceobjectwrapper import SliceObjectWrapper
from model.sliceobject import SliceObject
from model.slicehost import SliceHost
from datetime import datetime, timezone
import numpy as np
from auto_ts import auto_timeseries
import pandas as pd

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

    def add_slice_data_from_dump(self, dump_data : dict, occurence : int):
        if(len(dump_data.keys()) == 0):
            print("Empty data on slice encountered on dump " + self.host_name)
            return
        slice_host = SliceHost(slice_object=self.get_slice_object_from_dump(dump_data=dump_data["node"], occurence=occurence, epoch=dump_data["epoch"][occurence]),
                        vm_list=dump_data["node"]["vm_list"][occurence])
        self.add_slice(slice_host)

    def get_host_config(self):
        cpu_config_list = self.get_slices_metric("cpu_config")
        mem_config_list = self.get_slices_metric("mem_config")
        if cpu_config_list:
            cpu_config = cpu_config_list[-1]
        else:
            cpu_config=-1
        if mem_config_list:
            mem_config = mem_config_list[-1]
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

    def does_last_slice_contain_a_new_vm(self):
        # VM name is supposed unique
        for vm in self.get_last_slice().get_vm_list():
            if not self.get_oldest_slice().is_vm_in(vm):
                return True
        return False

    def is_stable(self): # Host is considered stable if no new VM were deployed
        if not self.is_historical_full():
            return False
        return True
        # self.get_last_slice().has_model ?
        data = dict()
        # dict_keys(['time', 'cpi', 'cpu', 'cpu_time', 'cpu_usage', 'elapsed_cpu_time', 'elapsed_time', 'freq', 'hwcpucycles', 'hwinstructions', 'maxfreq', 'mem', 'mem_usage', 'minfreq', 'oc_cpu', 'oc_cpu_d', 'oc_mem', 'oc_mem_d', 'sched_busy', 'sched_runtime', 'sched_waittime', 'swpagefaults', 'vm_number', 'vm'])
        data["time"] = [datetime.fromtimestamp(x) for x in self.get_slices_raw_metric("time")]
        data["cpu_usage"] = self.get_slices_raw_metric("cpu_usage")
        dataframe = pd.DataFrame(data)
        model = auto_timeseries(score_type='rmse', time_interval='S', seasonality=True, seasonal_period=360, verbose=1)
        model.fit(traindata=dataframe, ts_column="time", target="cpu_usage", cv=5,) 
        
        predictions = model.predict(testdata=5, model = 'best')
        print(predictions)
        return True

    # Host tiers as threshold
    def get_cpu_tiers(self): # return tier0, tier1
        self.is_stable()
        cpu_tier0 = self.round_to_upper_nearest(x=self.get_slices_max_metric(cpu_percentile=95), nearest_val=0.1) # unity is vcpu
        cpu_tier1 = cpu_tier0 # self.round_to_upper_nearest(x=self.get_slices_max_metric(cpu_percentile=99), nearest_val=0.1) # unity is vcpu
        return cpu_tier0, cpu_tier1
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

    # Mem tiers as threshold
    def get_mem_tiers(self): # return tier0, tier1
        mem_tier0 = self.round_to_upper_nearest(x=self.get_slices_max_metric(mem_percentile=50), nearest_val=1) # unity is MB
        mem_tier1 = mem_tier0 # self.round_to_upper_nearest(x=self.get_slices_max_metric(mem_percentile=99), nearest_val=1) # unity is MB
        return mem_tier0, mem_tier1

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