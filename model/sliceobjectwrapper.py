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
        # Update wrapper metrics
        self.object_seen+=1
        self.object_last_seen = int(data['time'][-1])
        sliceObject = SliceObject(raw_data=data)
        return sliceObject

    def get_slice_object_from_dump(self, dump_data : dict, occurence : int, epoch : int):
        # Update wrapper metrics
        self.object_seen+=1
        self.object_last_seen = epoch
        sliceObject = SliceObject(raw_data=dump_data["raw_data"][occurence])
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
    
    def get_oldest_slice(self):
        return self.slice_object_list[0]

    def round_to_upper_nearest(self, x : int, nearest_val : int):
        return nearest_val * math.ceil(x/nearest_val)