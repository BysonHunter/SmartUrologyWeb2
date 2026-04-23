import buildObj.Constants as Const


def is_in_other_slice(cur, other):
    is_in_x = other.min_x < cur.x < other.max_x
    is_in_z = other.min_z < cur.z < other.max_z
    return is_in_x and is_in_z


def is_in_left_kidney_constraints(slice):
    is_x_in_constraints = Const.left_kidney_center_constaints_x[0] < slice.x < \
                          Const.left_kidney_center_constaints_x[1]
    is_z_in_constraints = Const.left_kidney_center_constaints_z[0] < slice.z < \
                          Const.left_kidney_center_constaints_z[1]
    return is_x_in_constraints and is_z_in_constraints


def is_in_right_kidney_constraints(slic):
    is_x_in_constraints = Const.right_kidney_center_constaints_x[0] < slic.x < \
                          Const.right_kidney_center_constaints_x[1]
    is_z_in_constraints = Const.right_kidney_center_constaints_z[0] < slic.z < \
                          Const.right_kidney_center_constaints_z[1]
    return is_x_in_constraints and is_z_in_constraints


def is_stone(slic):
    return slic.label == Const.staghorn_stones or slic.label == Const.stone


def is_right_kidney(slic):
    return slic.label == Const.right_kidney or slic.label == Const.right_kidney_pieloectasy


def is_left_kidney(slic):
    return slic.label == Const.left_kidney or slic.label == Const.left_kidney_pieloectasy


def get_array_indexes(x_beg, x_end, z_beg, z_end, shape):
    return int(shape[2] * x_beg), int(shape[2] * x_end), int(shape[0] * z_beg), int(shape[0] * z_end)


def get_array_indexes_2d(x_beg, x_end, z_beg, z_end, shape):
    return int(shape[1] * x_beg), int(shape[1] * x_end), int(shape[0] * z_beg), int(shape[0] * z_end)


def get_subarray_2d(x_beg, x_end, z_beg, z_end, array):
    x_begin_scaled, x_end_scaled, z_begin_scaled, z_end_scaled = get_array_indexes_2d(x_beg, x_end, z_beg, z_end,
                                                                                      array.shape)
    return array[z_begin_scaled:z_end_scaled, x_begin_scaled:x_end_scaled]


def get_array_indexes_from_object_2d(obj, shape):
    return get_array_indexes_2d(obj.min_x, obj.max_x, obj.min_z, obj.max_z, shape)


def get_indexes_from_object(obj, array):
    return get_array_indexes(obj.min_x, obj.max_x, obj.min_z, obj.max_z, array.shape)


def is_slices_overlaps(first, second):
    is_x_overlaps = (first.min_x < second.min_x < first.max_x) or (first.min_x < second.max_x < first.max_x)
    is_y_overlaps = (first.min_z < second.min_z < first.max_z) or (first.min_z < second.max_z < first.max_z)
    return is_x_overlaps and is_y_overlaps


def slices_and(first, second):
    overlap_min_x = max(first.min_x, second.min_x)
    overlap_max_x = min(first.max_x, second.max_x)
    overlap_min_z = max(first.min_z, second.min_z)
    overlap_max_z = min(first.max_z, second.max_z)
    return overlap_min_x, overlap_max_x, overlap_min_z, overlap_max_z


def slices_or(first, second):
    or_min_x = min(first.min_x, second.min_x)
    or_max_x = max(first.max_x, second.max_x)
    or_min_z = min(first.min_z, second.min_z)
    or_max_z = max(first.max_z, second.max_z)
    return or_min_x, or_max_x, or_min_z, or_max_z
