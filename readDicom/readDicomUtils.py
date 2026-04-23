import os
import numpy as np
import cv2
import datetime
import csv
from readDicom.readDICOMDIR import readDICOMDIR
from readDicom.readDicomFiles import readDicomFiles

from readDicom.constants import *


def readDicomFolder(dicom_path, images_path, selected_series=None):
    """
    Чтение DICOM папки
    
    Args:
        dicom_path: Путь к папке с DICOM файлами
        images_path: Путь для сохранения изображений
        selected_series: Номер выбранной серии (опционально)
        
    Returns:
        Если selected_series is None: возвращает информацию о доступных сериях
        Если selected_series указан: возвращает путь к папке с результатами
    """
    # get date and time
    now = datetime.datetime.now()

    # Проверяем наличие DICOMDIR
    dicom_current_dir_path = (dicom_path + '/DICOMDIR') \
        if os.path.isfile(dicom_path + '/DICOMDIR') \
        else None

    if dicom_current_dir_path is not None:
        # Если серия не выбрана, получаем информацию о всех сериях
        if selected_series is None:
            result = readDICOMDIR(dicom_current_dir_path, None)
            # Убедимся, что все строки конвертированы
            if isinstance(result, dict) and 'available_series' in result:
                for series in result['available_series']:
                    for key in series:
                        if not isinstance(series[key], (str, int, float, bool, type(None))):
                            series[key] = str(series[key])
            return result
        # Если серия выбрана, загружаем ее
        slices = readDICOMDIR(dicom_current_dir_path, selected_series)
    else:
        # Если серия не выбрана, получаем информацию о всех сериях
        if selected_series is None:
            result = readDicomFiles(dicom_path, None)
            # Убедимся, что все строки конвертированы
            if isinstance(result, dict) and 'available_series' in result:
                for series in result['available_series']:
                    for key in series:
                        if not isinstance(series[key], (str, int, float, bool, type(None))):
                            series[key] = str(series[key])
            return result
        # Если серия выбрана, загружаем ее
        slices = readDicomFiles(dicom_path, selected_series)

    # Если slices - это dict (информация о сериях), возвращаем его
    if isinstance(slices, dict):
        return slices

    # Если это список срезов, продолжаем обработку
    if not slices:
        raise ValueError("Не удалось загрузить срезы DICOM")
    
    # Calculate frame size for image
    Length_image = slices[0].Rows * slices[0].PixelSpacing[0]
    Height_image = abs((slices[0].SliceLocation - slices[-1].SliceLocation))
    frameSize = (slices[0].Rows, int(slices[0].Rows * (Height_image / Length_image)))
    
    pixel_array = get_pixels_hu(slices)

    # set path to save images
    patID = str(slices[0].PatientID)[:8]
    patName = str(slices[0].PatientName).strip('^')
    save_dir = os.path.join(images_path, patID)
    save_dir = save_dir + '/' + str(now.strftime("%d%m%y"))

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # get images from array and store to output directory
    get_images_from_slice(pixel_array, save_dir, slices, frameSize)
    save_array(pixel_array, save_dir, slices)

    return save_dir


def read_dicom_set(dicom_path, selected_series):
    """
    Чтение конкретной DICOM серии
    
    Args:
        dicom_path: Путь к DICOM файлам
        selected_series: Номер выбранной серии
        
    Returns:
        (slices, frameSize): Кортеж со срезами и размером кадра
    """
    dicom_current_dir_path = (dicom_path + '/DICOMDIR') \
        if os.path.isfile(dicom_path + '/DICOMDIR') \
        else None

    if dicom_current_dir_path is not None:
        slices = readDICOMDIR(dicom_current_dir_path, selected_series)
    else:
        slices = readDicomFiles(dicom_path, selected_series)

    # Calculate frame size for image
    if slices and len(slices) > 0:
        Length_image = slices[0].Rows * slices[0].PixelSpacing[0]
        Height_image = abs((slices[0].SliceLocation - slices[-1].SliceLocation))
        frameSize = (slices[0].Rows, int(slices[0].Rows * (Height_image / Length_image)))
        return slices, frameSize
    
    return None, None


def get_pixels_hu(scans):
    image = np.stack([s.pixel_array for s in scans])
    # Convert to int16 (from sometimes int16),
    # should be possible as values should always be low enough (<32k)
    image = image.astype(np.int32)
    # Set outside-of-scan pixels to 1
    # The intercept is usually -1024, so air is approximately 0
    image[image == -2000] = 0

    # Convert to Hounsfield units (HU)
    intercept = scans[0].RescaleIntercept
    slope = scans[0].RescaleSlope
    if slope != 1:
        image = slope * image.astype(np.float64)
        image = image.astype(np.int32)
    image += np.int32(intercept)

    return np.array(image, dtype=np.int32)


def map2win(image_arr, window_level=30, window_width=450):
    """
     The purpose is to map the pixel values of the CT image (usually in a wide range, -2048~2048) to a fixed
            Within the scope, the mapping function needs to be calculated in conjunction with the window width window.
            Window  width of lung parenchyma
     window_level = -450~-600
     window_width = 1500~2000
    """
    window_max = window_level + 0.5 * window_width
    window_min = window_level - 0.5 * window_width
    index_min = image_arr < window_min
    index_max = image_arr > window_max
    #     index_mid = np.where((image >= window_min)&(image <= window_max))
    image_arr = (image_arr - window_min) / (window_width / 256) - 1
    image_arr[index_min] = 0
    image_arr[index_max] = 255
    return image_arr


def save_slice_to_image(image_name, slice_array, window_level, window_width,
                        frame_Size):  # improvement of image and save to dir
    slice_array = map2win(slice_array, window_level, window_width)
    x_size, y_size = frame_Size
    if x_size < 200:
        x_size = 200
    if y_size < 200:
        y_size = 200
    frame_Size = (x_size, y_size)
    slice_array = cv2.resize(slice_array.astype(np.int16), frame_Size,
                             interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(image_name, slice_array)
    return


def get_images_from_slice(data_array, images_path, slices, frameSize):
    now = datetime.datetime.now()
    start_pos = (slices[0].Columns // 2) - int(img_count) // 2
    stop_pos = (slices[0].Columns // 2) + int(img_count) // 2

    # get images and store to output directory
    count = 0
    dir_info = os.path.join(images_path + '/' + str(now.strftime("%d%m%y")) + 'dirinfo.txt')
    with open(dir_info, 'w') as f:
        f.write(f'Изображения, полученные по результатам компьютерной томографии\n')
        f.write(f'Пациент: {slices[0].PatientName}, код пациента {slices[0].PatientID}\n')
        f.write(f'Дата проведения исследования КТ: {slices[0].StudyDate}\n')
        f.write(f'Дата получения изображений из КТ: {now.strftime("%d-%m-%Y %H:%M")}\n')
        f.write(f'Размер изображения: {frameSize} \n')
        f.write(f'Список файлов изображений из КТ:\n')
        for y in range(start_pos, stop_pos):
            # filename of image
            out_image_name = os.path.join(
                images_path + '/' + str(slices[0].PatientID)[:8] + '_'
                + str(y) + '.' + str(img_format))
            out_image_name = out_image_name.strip(' ')
            coronal_slice = data_array[:, y, :]
            save_slice_to_image(out_image_name, coronal_slice, slices[0].WindowCenter,
                                slices[0].WindowWidth, frameSize)
            count += 1
            f.write(f'{out_image_name}\n')
        f.write(f'Всего сформировано файлов изображений из КТ: {count}\n')


def save_array(array, save_dir, slices):
    # save numpy array from dicom
    patient_ID = slices[0].PatientID[:8]
    numpy_array_name = save_dir + '/' + patient_ID + 'array.npy'
    np.save(numpy_array_name, array)
    array_info = save_dir + '/' + patient_ID + 'arrayinfo.csv'
    array_info_txt = save_dir + '/' + patient_ID + 'arrayinfo.txt'
    with open(array_info, mode="w", encoding='utf-8', newline="") as w_file:
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
                      "X",
                      "Window Center",
                      "Window Width"
                      ]
        file_writer = csv.DictWriter(w_file, fieldnames=fieldnames, delimiter=',')
        file_writer.writeheader()
        file_writer.writerow({
            "Study Date": slices[0].StudyDate,
            "Series Description": slices[0].SeriesDescription,
            "Patient's Name": slices[0].PatientName,
            "Patient ID": slices[0].PatientID,
            "Spacing Between Slices": slices[0].SpacingBetweenSlices,
            "Series Number": slices[0].SeriesNumber,
            "Start Slice Location": slices[0].SliceLocation,
            "End Slice Location": slices[-1].SliceLocation,
            "Slice Thickness": slices[0].SliceThickness,
            "Rows": slices[0].Rows,
            "Columns": slices[0].Columns,
            "Samples per Pixel": slices[0].SamplesPerPixel,
            "Pixel Spacing X": slices[0].PixelSpacing[0],
            "Pixel Spacing Y": slices[0].PixelSpacing[1],
            "Rescale Intercept": slices[0].RescaleIntercept,
            "Rescale Slope": slices[0].RescaleSlope,
            "Shape Z, Y, X": array.shape,
            "Z": array.shape[0],
            "Y": array.shape[1],
            "X": array.shape[2],
            "Window Center": slices[0].WindowCenter,
            "Window Width": slices[0].WindowWidth
        })

    with open(array_info_txt, 'w') as f:
        f.write(f'Study Date: {slices[0].StudyDate}\n')
        f.write(f'Series Description: {slices[0].SeriesDescription}\n')
        f.write(f"Patient's Name: {slices[0].PatientName}\n")
        f.write(f"Patient ID: {slices[0].PatientID}\n")
        f.write(f"Spacing Between Slices: {slices[0].SpacingBetweenSlices}\n")
        f.write(f"Series Number: {slices[0].SeriesNumber}\n")
        f.write(f"Start Slice Location: {slices[0].SliceLocation}\n")
        f.write(f"End Slice Location: {slices[-1].SliceLocation}\n")
        f.write(f"Slice Thickness: {slices[0].SliceThickness}\n")
        f.write(f"Rows: {slices[0].Rows}\n")
        f.write(f"Columns: {slices[0].Columns}\n")
        f.write(f"Samples per Pixel: {slices[0].SamplesPerPixel}\n")
        f.write(f"Pixel Spacing X: {slices[0].PixelSpacing[0]}\n")
        f.write(f"Pixel Spacing Y: {slices[0].PixelSpacing[1]}\n")
        f.write(f"Rescale Intercept: {slices[0].RescaleIntercept}\n")
        f.write(f"Rescale Slope: {slices[0].RescaleSlope}\n")
        f.write(f"Shape of array Z, Y, X: {array.shape}\n")
        f.write(f"Window Center: {slices[0].WindowCenter}\n")
        f.write(f"Window Width: {slices[0].WindowWidth}\n")


def rem_spase(s):
    s = s.strip().split(" ")
    s = "_".join(s)
    s = s.strip().split("^")
    s = "_".join(s)
    return s


def change_slash(s):
    return '/'.join(s.strip().split('\\'))