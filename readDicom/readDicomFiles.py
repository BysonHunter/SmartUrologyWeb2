import os
import pydicom
from readDicom.getSeriesNumber import getSeriesNumber


def readDicomFiles(dicom_path, selected_series=None):
    """Reads DICOM files from a directory and returns a sorted list of datasets.
    
    Args:
        dicom_path (str): Path to the directory containing DICOM files.
        selected_series (int, optional): Номер выбранной серии. 
                                        Если None, возвращает информацию о всех сериях.
        
    Returns:
        list: A list of sorted DICOM datasets если серия выбрана,
              или dict с информацией о сериях если selected_series is None.
    """
    slices = []
    series_dict = {}

    # Read DICOM files from the directory
    print(f"Сканирование DICOM файлов в: {dicom_path}")
    for filename in os.listdir(dicom_path):
        filepath = os.path.join(dicom_path, filename)
        if filename.lower().endswith((".dcm", ".ima")):  # Check for common DICOM extensions
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=True)
                slices.append(ds)
            except pydicom.errors.InvalidDicomFile:
                print(f"Skipping invalid DICOM file: {filepath}")
                continue
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue

    # Если не указана серия, возвращаем информацию о всех сериях
    if selected_series is None:
        if slices:
            # Группируем по сериям
            for slic in slices:
                if hasattr(slic, 'SeriesNumber'):
                    series_num = slic.SeriesNumber
                    if series_num not in series_dict:
                        series_dict[series_num] = {
                            "number": series_num,
                            "description": str(getattr(slic, 'SeriesDescription', 'Unknown')),
                            "image_count": 0,
                            "modality": str(getattr(slic, 'Modality', 'CT'))
                        }
                    series_dict[series_num]["image_count"] += 1
            
            series_list = list(series_dict.values())
            
            # Получаем информацию о пациенте из первого среза
            patient_info = {}
            if slices:
                try:
                    patient_info = {
                        "patient_name": str(getattr(slices[0], 'PatientName', 'Unknown')),
                        "patient_id": str(getattr(slices[0], 'PatientID', 'Unknown')),
                        "study_date": str(getattr(slices[0], 'StudyDate', ''))
                    }
                except:
                    patient_info = {
                        "patient_name": "Unknown",
                        "patient_id": "Unknown",
                        "study_date": ""
                    }
            
            return {
                "available_series": series_list,
                "patient_info": patient_info
            }
        else:
            return {
                "available_series": [],
                "patient_info": {}
            }

    # Если указана серия, загружаем ее срезы
    selected_slices = []
    for filename in os.listdir(dicom_path):
        filepath = os.path.join(dicom_path, filename)
        if filename.lower().endswith((".dcm", ".ima")):
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=False)
                if hasattr(ds, 'SeriesNumber') and ds.SeriesNumber == selected_series:
                    selected_slices.append(ds)
            except:
                continue

    if not selected_slices:
        print(f"No slices found for selected series: {selected_series}")
        return []

    # Remove datasets without SliceLocation
    new_slices = [slic for slic in selected_slices if hasattr(slic, 'SliceLocation')]

    # Remove datasets with different pixel array shapes
    if new_slices:
        sh = new_slices[0].pixel_array.shape
        new_slices = [slic for slic in new_slices if slic.pixel_array.shape == sh]

    # Sort slices
    if new_slices and (new_slices[0].InstanceNumber < new_slices[-1].InstanceNumber) and (
            new_slices[0].SliceLocation < new_slices[-1].SliceLocation):
        new_slices = sorted(new_slices, key=lambda s1: s1.InstanceNumber)
    elif new_slices:
        new_slices = sorted(new_slices, reverse=True, key=lambda s1: s1.SliceLocation)

    return new_slices