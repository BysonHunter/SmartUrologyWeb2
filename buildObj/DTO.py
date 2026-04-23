class SliceDTO:
    def __init__(self, label, x, z, w, h, conf):
        self.label = label
        self.x = x
        self.z = z
        self.w = w
        self.h = h
        self.conf = conf
        
        self.min_x = self.x - w / 2
        self.max_x = self.x + w / 2
        self.min_z = self.z - h / 2
        self.max_z = self.z + h / 2
        
        
class LayerDTO:
    def __init__(self, y, slice_list):
        self.y = y
        self.slice_list = slice_list
        
        
class ObjectParamsDto:
    def __init__(self, x_center, z_center, w, h, number, first_index, last_index):
        self.x_center = x_center
        self.z_center = z_center
        self.w = w
        self.h = h
        self.number = number
        self.first_index = first_index
        self.last_index = last_index
