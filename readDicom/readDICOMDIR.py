import os
import pydicom
from pathlib import Path
from readDicom.getSeriesNumber import getSeriesNumber


def readDICOMDIR(dicom_dir_path, selected_series_number=None):
    """Reads a DICOMDIR file and returns a list of sorted DICOM datasets.
    
    Args:
        dicom_dir_path (str): Path to the DICOMDIR file.
        selected_series_number (int, optional): Номер выбранной пользователем серии.
                                               Если None, вернет информацию о всех сериях.
        
    Returns:
        list: A list of sorted DICOM datasets if series selected, 
              or dict with series info if series_number is None.
    """

    image_filenames = []
    SeriesNumbers = []
    SeriesDescription = []
    CountOfImages = []
    slices = []

    # Resolve the parent directory for ReferencedFileID paths
    root_dir = Path(dicom_dir_path).resolve().parent

    # Read the DICOMDIR file
    try:
        ds = pydicom.dcmread(dicom_dir_path)
    except Exception as e:
        print(f"Ошибка при чтении DICOMDIR файла: {e}")
        return {"available_series": [], "patient_info": {}}

    # Извлекаем информацию о пациенте
    patient_info = {}
    try:
        patient_info = {
            'patient_name': str(getattr(ds, 'PatientName', 'Unknown')),
            'patient_id': str(getattr(ds, 'PatientID', 'Unknown')),
            'study_date': str(getattr(ds, 'StudyDate', ''))
        }
    except:
        patient_info = {
            'patient_name': 'Unknown',
            'patient_id': 'Unknown', 
            'study_date': ''
        }

    # Iterate through the PATIENT records
    for patient in ds.patient_records:

        # Find all the STUDY records for the patient
        studies = [ii for ii in patient.children if ii.DirectoryRecordType == "STUDY"]
        for study in studies:
            # Find all the SERIES records in the study
            all_series = [ii for ii in study.children if ii.DirectoryRecordType == "SERIES"]
            for series in all_series:
                # Find all the IMAGE records in the series
                images = [ii for ii in series.children if ii.DirectoryRecordType == "IMAGE"]

                descr = getattr(series, "SeriesDescription", None)
                if descr:  # Check if SeriesDescription is not None
                    SeriesNumbers.append(series.SeriesNumber)
                    SeriesDescription.append(str(descr))  # Преобразуем в строку
                    CountOfImages.append(len(images))

    # Если номер серии не указан, возвращаем информацию о всех сериях
    if selected_series_number is None:
        series_info = getSeriesNumber(SeriesNumbers, SeriesDescription, CountOfImages)
        
        # Добавляем модальность к каждой серии
        for series in series_info:
            series['modality'] = 'CT'  # По умолчанию CT, можно извлечь из DICOM если нужно
        
        return {
            "available_series": series_info,
            "patient_info": patient_info
        }

    # Find the selected series and get image file names
    for patient in ds.patient_records:
        studies = [ii for ii in patient.children if ii.DirectoryRecordType == "STUDY"]
        for study in studies:
            all_series = [ii for ii in study.children if
                          ii.DirectoryRecordType == "SERIES" and ii.SeriesNumber == selected_series_number]
            for series in all_series:
                image_records = series.children
                image_filenames = [os.path.join(root_dir, *image_rec.ReferencedFileID)
                                   for image_rec in image_records]

    # Read the DICOM images from the filenames
    for file in image_filenames:
        try:
            slices.append(pydicom.dcmread(file))
        except:
            continue

    # Remove datasets without SliceLocation attribute
    new_slices = [f for f in slices if hasattr(f, 'SliceLocation')]

    # Remove datasets with different pixel array shapes (Assuming they should be the same)
    if new_slices:
        sh = new_slices[0].pixel_array.shape
        new_slices = [s for s in new_slices if sh == s.pixel_array.shape]

    # Sort the slices based on SliceLocation and InstanceNumber
    if new_slices and (new_slices[0].InstanceNumber < new_slices[-1].InstanceNumber) and (
            new_slices[0].SliceLocation < new_slices[-1].SliceLocation):
        new_slices = sorted(new_slices, key=lambda s: s.InstanceNumber)
    elif new_slices:
        new_slices = sorted(new_slices, reverse=True, key=lambda s: s.SliceLocation)

    return new_slices