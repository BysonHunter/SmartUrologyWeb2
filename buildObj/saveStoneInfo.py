import csv


def saveStoneInfoToCSV(stone_param, filenameCSV):
    with open(filenameCSV, mode="w", encoding='utf-8', newline="") as w_file:
        fieldnames = [
            "index",  # 0
            "med_slice",  # 1
            "Length_stone",  # 2
            "Height_stone",  # 3
            "Depth_stone",  # 4
            "volume_unit_vox",  # 5
            "volume_unit_sm",  # 6
            "volume_stone1",  # 7
            "volume_stone",  # 8
            "count_stone_vox",  # 9
            "mass_stone",  # 10
            "ave_dens",  # 11
            "ave_mass_stone",  # 12
            "max_HU",  # 13
            "min_HU",  # 14
            "ave_HU",  # 15
            "x_beg",  # 16
            "x_end",  # 17
            "z_beg",  # 18
            "z_end",  # 19
            "start_slice",  # 20
            "end_slice",  # 21
            "realLength_stone",  # 22
            "realHeight_stone",  # 23
            "frame_size_stone"  # 24
            ]
        file_writer = csv.DictWriter(w_file, fieldnames=fieldnames, delimiter=',')
        file_writer.writeheader()
        file_writer.writerow({
            "index": stone_param[0],
            "med_slice": stone_param[1],  # 1
            "Length_stone": stone_param[2],  # 2
            "Height_stone": stone_param[3],  # 3
            "Depth_stone": stone_param[4],  # 4
            "volume_unit_vox": stone_param[5],  # 5
            "volume_unit_sm": stone_param[6],  # 6
            "volume_stone1": stone_param[7],  # 7
            "volume_stone": stone_param[8],  # 8
            "count_stone_vox": stone_param[9],  # 9
            "mass_stone": stone_param[10],  # 10
            "ave_dens": stone_param[11],  # 11
            "ave_mass_stone": stone_param[12],  # 12
            "max_HU": stone_param[13],  # 13
            "min_HU": stone_param[14],  # 14
            "ave_HU": stone_param[15],  # 15
            "x_beg": stone_param[16],  # 16
            "x_end": stone_param[17],  # 17
            "z_beg": stone_param[18],  # 18
            "z_end": stone_param[19],  # 19
            "start_slice": stone_param[20],  # 20
            "end_slice": stone_param[21],  # 21
            "realLength_stone": stone_param[22],  # 22
            "realHeight_stone": stone_param[23],  # 23
            "frame_size_stone": stone_param[24]  # 24
        })
