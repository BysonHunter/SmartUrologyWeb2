import csv
import os
from os import listdir
from pathlib import Path
from sys import maxsize as max_int_size
import shutil

from buildObj.Utils import *
from buildObj.classObj import *
import buildObj.Constants as Constants
from buildObj.visual_3d import *
from buildObj.saveStoneInfo import saveStoneInfoToCSV
from buildObj.pdfWork import create_PDF
from readDicom.constants import img_format

min_int_size = -max_int_size - 1


def main(input_path):
    global stone_param, \
        index_kidney, \
        norm_stone_image, \
        frame_size_stone, \
        ds_array, \
        z_beg, \
        z_end, \
        start_slice, \
        end_slice, \
        x_beg, \
        x_end, \
        med_slice, \
        realLength_stone, \
        realHeight_stone

    def get_kidney_info(kidney):
        first = max_int_size
        last = min_int_size
        max_square = min_int_size
        max_square_index = 0
        max_square_center = (0, 0)
        max_w = min_int_size
        max_h = min_int_size
        size = 0
        cur_kidney_type = kidney_type.normal
        for (key, value) in filter(lambda x: x[1], kidney.items()):
            size += 1
            first = min(key, first)
            last = max(key, last)
            cur_square = value.w * value.h
            if cur_square > max_square:
                max_square = cur_square
                max_square_index = key
                max_square_center = (value.x, value.z)
                max_w = value.w
                max_h = value.h

            if value.label == Constants.left_kidney_pieloectasy or value.label == Constants.right_kidney_pieloectasy:
                cur_kidney_type = kidney_type.pieloectasy

        return ObjectParamsDto(
            x_center=max_square_center[0],
            z_center=max_square_center[1],
            w=max_w,
            h=max_h,
            number=max_square_index,
            first_index=first,
            last_index=last
        )

    ''' находится ли объект в ограничениях для правой почки '''

    def right_kidney_condition(slice):
        return is_right_kidney(slice) and is_in_right_kidney_constraints(slice)

    ''' находится ли объект в ограничениях для левой почки '''

    def left_kidney_condition(slice):
        return is_left_kidney(slice) and is_in_left_kidney_constraints(slice)

    ''' выбрать почку с максимальным правдоподобием '''

    def kidney_with_max_conf(lst):
        if not len(lst):
            return None
        return max(lst, key=lambda x: x.conf)

    ''' выбрать правую почку с максимальным правдоподобием '''

    def right_kidney_with_max_conf(lst):
        return kidney_with_max_conf(list(filter(right_kidney_condition, lst)))

    ''' выбрать левую почку с максимальным правдоподобием'''

    def left_kidney_with_max_conf(lst):
        return kidney_with_max_conf(list(filter(left_kidney_condition, lst)))

    def get_kidney_array(kidney_list, lightHU_array):
        kidney_info = get_kidney_info(kidney_list)
        x_begin_scaled, x_end_scaled, z_begin_scaled, z_end_scaled = get_indexes_from_object(
            kidney_list[kidney_info.number], lightHU_array)
        return lightHU_array[
               z_begin_scaled:z_end_scaled,
               kidney_info.first_index:kidney_info.last_index,
               x_begin_scaled:x_end_scaled
               ]

    def stone_clusterize(stone_dict):
        stones = []
        for (key, layer) in stone_dict.items():
            for cur_slice in layer:
                cur_stone = {key: [cur_slice]}
                overlaps_stones = []
                for (i, prev_stone) in enumerate(stones):
                    if key - 1 in prev_stone:
                        prev_layer = prev_stone[key - 1]
                        for prev_slice in prev_layer:
                            if is_in_other_slice(prev_slice, cur_slice) or is_in_other_slice(cur_slice,
                                                                                             prev_slice):
                                overlaps_stones.append(prev_stone)
                                break
                for overlaps_stone in overlaps_stones:
                    for (prev_key, prev_layer) in overlaps_stone.items():
                        if prev_key in cur_stone:
                            cur_stone[prev_key] = [*cur_stone[prev_key], *prev_layer]
                        else:
                            cur_stone[prev_key] = prev_layer
                    stones.remove(overlaps_stone)

                stones.append(cur_stone)
        return stones

    def stone_info(stone_list):
        array = load_numpy_array()
        res = []
        for (i, stone) in enumerate(stone_list):
            first = max_int_size
            last = min_int_size
            max_light = min_int_size
            max_light_index = 0
            max_light_center = (0, 0)
            max_light_params = (0, 0)
            for (key, layer) in stone.items():
                first = min(key, first)
                last = max(key, last)
                for cur_slice in layer:
                    x_begin_scaled, x_end_scaled, z_begin_scaled, z_end_scaled = get_indexes_from_object(
                        cur_slice,
                        array)
                    cur_light = array[z_begin_scaled:z_end_scaled, key, x_begin_scaled:x_end_scaled].sum()
                    if cur_light > max_light:
                        max_light = cur_light
                        max_light_index = key
                        max_light_center = (cur_slice.x, cur_slice.z)
                        max_light_params = (cur_slice.w, cur_slice.h)
            res.append(ObjectParamsDto(
                x_center=max_light_center[0],
                z_center=max_light_center[1],
                w=max_light_params[0],
                h=max_light_params[1],
                number=max_light_index,
                first_index=first,
                last_index=last
            ))

        return res

    # define dir of output stones parameters
    def get_output_path():
        if not os.path.exists(stones_dir_path):
            os.makedirs(stones_dir_path)
            print('Создан каталог ', stones_dir_path)
        return stones_dir_path

    # load array
    def load_numpy_array():
        dataset_array = np.load(numpy_file_path).astype(np.int16)
        return dataset_array

    def get_filename_param_csv():
        return filename_param_csv_path

    # get parameters of found stones
    def get_found_stones_param(index, kidney_position):
        global stone
        if kidney_position == 'left':
            stone = left_stones_params[index]
        elif kidney_position == 'right':
            stone = right_stones_params[index]
        return (stone.x_center,
                stone.z_center,
                stone.w, stone.h,
                stone.first_index,
                stone.last_index,
                stone.number)

    # get parameters of numpy array
    def get_numpy_parameters(filename):
        param_num = []
        fieldnames = ["Study Date",
                      "Series Description",
                      "Patient's Name",
                      "Patient ID",
                      "Spacing Between Slices",
                      "Series Number",
                      "Start Slice Location",
                      "End Slice Location",
                      "Slice Thickness",
                      "Rows",
                      "Columns",
                      "Samples per Pixel",
                      "Pixel Spacing X",
                      "Pixel Spacing Y",
                      "Rescale Intercept",
                      "Rescale Slope",
                      "Shape Z, Y, X",
                      "Z",
                      "Y",
                      "X"
                      ]

        with open(filename, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for i in range(len(fieldnames)):
                    # print(row[fieldnames[i]])
                    param_num.append(row[fieldnames[i]])
        return param_num

    def calc_stone_parameters(index, kidney_position):
        global stone_param
        # filename_param_csv = get_filename_param_csv()
        param_numpy = get_numpy_parameters(get_filename_param_csv())
        ds_array = load_numpy_array()
        index_kidney = 'lk_' if kidney_position == 'left' else 'rk_'
        filename_stone_param = get_output_path() + 'stnpar_' + index_kidney + str(index) + '.txt'

        # StudyDate = param_numpy[0]
        # SeriesDescription = param_numpy[1]
        # PatientName = param_numpy[2]
        # PatientID = param_numpy[3]
        z_thin = float(param_numpy[4])
        # SeriesNumber = param_numpy[5]
        # StartSliceLocation = param_numpy[6]
        # EndSliceLocation = param_numpy[7]
        SliceThickness = float(param_numpy[8])
        # Rows = param_numpy[9]
        # Columns = param_numpy[10]
        # SamplesperPixel = param_numpy[11]
        x_thin = float(param_numpy[12])
        y_thin = float(param_numpy[13])
        # RescaleIntercept = param_numpy[14]
        # RescaleSlope = param_numpy[15]
        # ShapeZYX = param_numpy[16]
        z_ = int(param_numpy[17])
        # y_ = int(param_numpy[18])
        x_ = int(param_numpy[19])

        x_center, z_center, w, h, start_slice, end_slice, med_slice = get_found_stones_param(index, kidney_position)
        x_beg = int(x_ * (x_center - w / 2))
        x_end = int(x_ * (x_center + w / 2))
        z_beg = int(z_ * (z_center - h / 2))
        z_end = int(z_ * (z_center + h / 2))
        Length_stone = (x_end - x_beg)
        Height_stone = (z_end - z_beg)
        realLength_stone = Length_stone * x_thin
        realHeight_stone = Height_stone * z_thin
        x_frame = Length_stone
        y_frame = int(Length_stone * (realHeight_stone / realLength_stone))
        frame_size_stone = (x_frame, y_frame)
        stone_3d = ds_array[z_beg:z_end, start_slice:end_slice, x_beg:x_end]
        only_stone = []
        count_stone_vox = 0

        for z in range(stone_3d.shape[0]):
            for y in range(stone_3d.shape[1]):
                for x in range(stone_3d.shape[2]):
                    if stone_3d[z, y, x] > 160:
                        only_stone.append(stone_3d[z, y, x])
                        count_stone_vox += 1
                    else:
                        only_stone.append(0)
        only_stone = np.array(only_stone)
        only_stone = only_stone.reshape(stone_3d.shape)

        if np.any(only_stone != 0):
            max_HU = only_stone.max()
            min_HU = only_stone.max()
        else:
            max_HU = min_HU = 0

        # find min HU
        for z in range(only_stone.shape[0]):
            for y in range(only_stone.shape[1]):
                for x in range(only_stone.shape[2]):
                    if only_stone[z, y, x] != 0:
                        if only_stone[z, y, x] < min_HU:
                            min_HU = only_stone[z, y, x]

        # find average HU
        sum_HU = 0
        for z in range(only_stone.shape[0]):
            for y in range(only_stone.shape[1]):
                for x in range(only_stone.shape[2]):
                    if only_stone[z, y, x] != 0:
                        sum_HU += only_stone[z, y, x]
        ave_HU = (sum_HU / count_stone_vox) if count_stone_vox != 0 else 0

        # calc density of stones array
        dens_stone = []
        dens_stone_sum = 0
        for z in range(only_stone.shape[0]):
            for y in range(only_stone.shape[1]):
                for x in range(only_stone.shape[2]):
                    if only_stone[z, y, x] != 0:
                        dens_stone.append((only_stone[z, y, x] * 0.000485 + 1.539))
                        dens_stone_sum += (only_stone[z, y, x] * 0.000485 + 1.539)
                    else:
                        dens_stone.append(0)
        dens_stone = np.array(dens_stone)
        dens_stone = dens_stone.reshape(only_stone.shape)

        Length_stone = (x_end - x_beg) * x_thin / 10
        Height_stone = (z_end - z_beg) * z_thin / 10

        # calc volume of stone
        volume_unit_vox = x_thin * y_thin * z_thin
        volume_unit_sm = volume_unit_vox / 1000
        volume_stone = volume_unit_sm * count_stone_vox
        mass_stone = volume_unit_sm * dens_stone_sum
        volume_stone1 = volume_unit_sm * dens_stone.shape[0] * dens_stone.shape[1] * dens_stone.shape[2]

        if count_stone_vox > 0:
            ave_dens = dens_stone_sum / count_stone_vox
        else:
            ave_dens = 0

        # stone_param = []
        stone_param = [index,  # 0
                       med_slice,  # 1
                       Length_stone,  # 2
                       Height_stone,  # 3
                       volume_stone1 / (Length_stone * Height_stone),  # 4
                       volume_unit_vox,  # 5
                       volume_unit_sm,  # 6
                       volume_stone1,  # 7
                       volume_stone,  # 8
                       count_stone_vox,  # 9
                       mass_stone,  # 10
                       ave_dens,  # 11
                       ave_dens * volume_stone,  # 12
                       max_HU,  # 13
                       min_HU,  # 14
                       ave_HU,  # 15
                       x_beg,  # 16
                       x_end,  # 17
                       z_beg,  # 18
                       z_end,  # 19
                       start_slice,  # 20
                       end_slice,  # 21
                       realLength_stone,  # 22
                       realHeight_stone,  # 23
                       frame_size_stone]  # 24

        # save params of stone to csv file
        nameStoneParamCSV = get_output_path() + 'stnpar_' + index_kidney + str(index) + '.csv'
        saveStoneInfoToCSV(stone_param, nameStoneParamCSV)

        # save param`s of stone into text file
        with open(filename_stone_param, 'w') as f:
            f.write(f'Параметры камня: \n')
            f.write(f'{"Правая почка" if kidney_position == "right" else "Левая почка"}, камень {index}, ')
            # f.write(f'срез {list_slices_of_stones_RK[index_of_stone] if kidney_key == "right" else
            # list_slices_of_stones_LK[index_of_stone]}\n')
            f.write(
                f'размеры камня - {stone_param[2]:.2f} см Х {stone_param[3]:.2f} см Х {stone_param[4]:.2f} см \n')
            # s4 = f'объем 1 вокселя, мм3 - {stone_param[5]:.2f}, объем 1 вокселя, см3 - {stone_param[6]:.2f}\n'
            # s5 = f'объем пространства, см3 - {stone_param[7]:.2f}, объем камня, см3 - {stone_param[8]:.2f}\n'
            # s6 = f'количество вокселей в камне - {stone_param[9]}\n'
            f.write(f'масса камня, грамм -  {stone_param[10]:.2f}\n')
            f.write(f'средняя плотность, гр/см3 -  {stone_param[11]:.2f}\n')
            f.write(f'масса по средней плотности, грамм -  {stone_param[12]:.2f}\n')
            f.write(f'максимальная плотность по HU = {stone_param[13]}\n')
            f.write(f'минимальная плотность по HU = {stone_param[14]}\n')
            f.write(f'средняя плотность по HU = {stone_param[15]:.0f}\n')

        # calc new reduced density of stones array
        new_dens_stone = []
        for z in range(dens_stone.shape[0]):
            for y in range(dens_stone.shape[1]):
                for x in range(dens_stone.shape[2]):
                    if dens_stone[z, y, x] == 0:
                        new_dens_stone.append(0)
                    elif (dens_stone[z, y, x] < 1.75) and (dens_stone[z, y, x] > 0):
                        new_dens_stone.append(1.7)
                    elif (dens_stone[z, y, x] >= 1.75) and (dens_stone[z, y, x] < 1.85):
                        new_dens_stone.append(1.8)
                    elif (dens_stone[z, y, x] >= 1.85) and (dens_stone[z, y, x] < 1.95):
                        new_dens_stone.append(1.9)
                    elif (dens_stone[z, y, x] >= 1.95) and (dens_stone[z, y, x] < 2.05):
                        new_dens_stone.append(2.0)
                    elif (dens_stone[z, y, x] >= 2.05) and (dens_stone[z, y, x] < 2.15):
                        new_dens_stone.append(2.1)
                    elif (dens_stone[z, y, x] >= 2.15) and (dens_stone[z, y, x] < 2.25):
                        new_dens_stone.append(2.2)
                    elif (dens_stone[z, y, x] >= 2.25) and (dens_stone[z, y, x] < 2.35):
                        new_dens_stone.append(2.3)
                    elif dens_stone[z, y, x] >= 2.35:
                        new_dens_stone.append(2.4)
        new_dens_stone = np.array(new_dens_stone)
        new_dens_stone = new_dens_stone.reshape(dens_stone.shape)

        # save numpy array of HU of current stone
        np.save(get_output_path() + 'st_' + index_kidney + str(index), only_stone)

        # visualisation

        # copy image, where found this stone
        detImgWStoneSours = detectedImagesPath + param_numpy[3] + '_' + str(med_slice) + '.' + img_format
        detImgWStoneDest = stones_dir_path + param_numpy[3] + '_' + str(med_slice) + '.' + img_format
        shutil.copy(detImgWStoneSours, detImgWStoneDest)

        # plot slic stone image
        stone_image = ds_array[z_beg:z_end, med_slice, x_beg:x_end]
        real_stone_image = cv2.resize(stone_image, frame_size_stone)
        stone_slice_visualisation(real_stone_image, med_slice, realLength_stone, realHeight_stone,
                                  index_kidney + str(index))
        image_name = get_output_path() + 'stone_' + index_kidney + str(index) + '.png'
        plt.savefig(image_name, bbox_inches='tight', transparent=True, format='png')

        # plot 3D image of density of stones
        if only_stone.shape[0] >= 3 and only_stone.shape[1] >= 3 and only_stone.shape[2] >= 3:
            stone_vox3D_visualisation(only_stone[::-1, ::1, ::-1].T, SliceThickness, x_thin, y_thin, 12, 75)
            stone_image_name = get_output_path() + '/stone' + index_kidney + str(index) + '_1' + '.png'
            plt.savefig(stone_image_name, transparent=True, bbox_inches='tight', format='png')

        # plot 3D image of reduced density of stones
        if new_dens_stone.shape[0] >= 3 and new_dens_stone.shape[1] >= 3 and new_dens_stone.shape[2] >= 3:
            stone_vox3D_visualisation(new_dens_stone[::-1, ::1, ::-1].T, SliceThickness, x_thin, y_thin,
                                      12, 75, cm.Set1)
            stone_image_name = get_output_path() + '/stone' + index_kidney + str(index) + '_2' + '.png'
            plt.savefig(stone_image_name, transparent=True, bbox_inches='tight', format='png')

        # here you need to insert the output in PDF of the parameters of only current stone with pictures !!!!!!

        return stone_param

    input_path = str(input_path) + '/'
    labels_dir_path = input_path + 'detect/labels/'
    stones_dir_path = input_path + 'stones/'
    detectedImagesPath = input_path + 'detect/'

    # ID = str('/' + Path(input_path).parts[3][0:4])
    # ID = gi.patient_ID
    # filename_param_csv_path = input_path + ID + 'arrayinfo.csv'
    filename_param_csv_path = input_path + [f for f in listdir(input_path) if f.lower().endswith('.csv')][0]
    # param_numpy = get_numpy_parameters(get_filename_param_csv())
    param_numpy = get_numpy_parameters(filename_param_csv_path)

    labels_names = listdir(labels_dir_path)
    ID = param_numpy[3]
    SliceThickness = param_numpy[8]
    x_thin = param_numpy[12]
    y_thin = param_numpy[13]
    numpy_file_path = input_path + str(ID) + 'array.npy'
    light_array = np.load(numpy_file_path).astype(np.int16)
    parser = Parser()

    labels_list = sorted(map(lambda x: parser.parse(labels_dir_path, x), labels_names), key=lambda x: x.y)

    right_kidney_list = dict([(label.y, right_kidney_with_max_conf(label.slice_list)) for label in labels_list])
    left_kidney_list = dict([(label.y, left_kidney_with_max_conf(label.slice_list)) for label in labels_list])

    left_kidney_array = get_kidney_array(left_kidney_list, light_array)
    right_kidney_array = get_kidney_array(right_kidney_list, light_array)
    np.save(get_output_path() + 'LK', left_kidney_array)  # save left kidney numpy array
    np.save(get_output_path() + 'RK', right_kidney_array)  # save right kidney numpy array

    all_stones = dict([(label.y, list(filter(is_stone, label.slice_list))) for label in labels_list])
    stones_with_right_kidney = dict(filter(lambda x: right_kidney_list[x[0]], all_stones.items()))
    stones_with_left_kidney = dict(filter(lambda x: left_kidney_list[x[0]], all_stones.items()))

    for i in stones_with_right_kidney:
        stones_with_right_kidney[i] = list(
            filter(lambda x: is_in_other_slice(x, right_kidney_list[i]), stones_with_right_kidney[i]))
    for i in stones_with_left_kidney:
        stones_with_left_kidney[i] = list(
            filter(lambda x: is_in_other_slice(x, left_kidney_list[i]), stones_with_left_kidney[i]))

    left_stones_params = stone_info(stone_clusterize(stones_with_left_kidney))
    right_stones_params = stone_info(stone_clusterize(stones_with_right_kidney))

    list_slices_of_stones_RK = []
    list_slices_of_stones_LK = []

    RS_params = []
    LS_params = []

    # calculation stones parameters
    # for right kidney
    for i in range(len(right_stones_params)):
        kidney_key = 'right'
        calc_stone_parameters(i, kidney_key)
        list_slices_of_stones_RK.append(str(stone_param[1]))
        RS_params.append(stone_param)

    # for left kidney
    for i in range(len(left_stones_params)):
        kidney_key = 'left'
        calc_stone_parameters(i, kidney_key)
        list_slices_of_stones_LK.append(str(stone_param[1]))
        LS_params.append(stone_param)

    # here you need to insert the output in PDF of the parameters of the stones !!!!!!
    create_PDF(stones_dir_path, RS_params, LS_params, param_numpy)
    return stones_dir_path
