
import cv2
import matplotlib
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
# import plotly.graph_objs as go

from matplotlib import cm
from matplotlib import ticker
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axes_grid1 import make_axes_locatable


def normalize(arr):
    if np.any(arr != 0):
        arr_min = np.min(arr)
    else:
        arr_min = 0
    try:
        return (arr - arr_min) / (np.max(arr) - arr_min)
    except Exception:
        return arr


def explode(data):
    shape_arr = np.array(data.shape)
    size = shape_arr[:3] * 2 - 1
    exploded = np.zeros(np.concatenate([size, shape_arr[3:]]), dtype=data.dtype)
    exploded[::2, ::2, ::2] = data
    return exploded


def expand_coordinates(indices):
    x, y, z = indices
    x[1::2, :, :] += 1
    y[:, 1::2, :] += 1
    z[:, :, 1::2] += 1
    return x, y, z


def stone_slice_visualisation(current_stone_array, med_slice, realLength_stone, realHeight_stone, kid_stone_index):
    ticks = [0, 160, 300, 500, 800, 900, 1000, 1100, 1200, 1250, 1300]
    ticks_labels = ['0', '160', '300', '500', '800', '900', '1000', '1100', '1200', '1250', '1300HU']
    # Create figure and add axis
    # fig = plt.figure(figsize=(frame_size_stone), dpi=100)
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot()
    plt.xlabel('Width, mm', fontsize=10)
    plt.ylabel('Height, mm', fontsize=10)
    plt.title(f'Stone {kid_stone_index} at {med_slice} slice')
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
    # Show AFM image
    img = ax.imshow(current_stone_array, origin='upper', cmap=plt.cm.inferno,
                    extent=(0, realLength_stone, 0, realHeight_stone), vmin=0, vmax=1300)
    # Create axis for colorbar
    cbar_ax = make_axes_locatable(ax).append_axes(position='right', size='5%', pad=0.1)
    # Create colorbar
    cbar = fig.colorbar(mappable=img, cax=cbar_ax)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(ticks_labels)
    return fig


def stone_vox3D_visualisation(cube, SliceThickness=1, x_thin=1, y_thin=1, st_angle=15, angle=75, cmap=cm.afmhot):

    cube = np.asanyarray(cube, dtype=float)

    if cube.shape >= (4, 4, 4):
        dx = int(cube.shape[0] * 0.85)
        dy = int(cube.shape[1] * 0.85)
        dz = int(cube.shape[2] * 0.85)
    else:
        dx, dy, dz = cube.shape

    cube1 = cube[:dx, :dy, :dz].astype(float)
    cube = normalize(cube)
    cube1 = normalize(cube1)

    facecolors = cmap(cube)
    facecolors[:, :, :, -1] = cube
    facecolors = explode(facecolors)
    facecolors1 = cmap(cube1)
    facecolors1[:, :, :, -1] = cube1
    facecolors1 = explode(facecolors1)

    filled = facecolors[:, :, :, -1] != 0
    filled1 = facecolors1[:, :, :, -1] != 0
    x, y, z = expand_coordinates(np.indices(np.array(filled.shape) + 1))
    x1, y1, z1 = expand_coordinates(np.indices(np.array(filled1.shape) + 1))

    z = (z * x_thin if x_thin > 1 else z / x_thin)
    y = (y * y_thin if y_thin > 1 else y / y_thin)
    x = (x * SliceThickness if SliceThickness > 1 else x / SliceThickness)

    x1 = (x1 * x_thin if x_thin > 1 else x1 / x_thin)
    y1 = (y1 * y_thin if y_thin > 1 else y1 / y_thin)
    z1 = (z1 * SliceThickness if SliceThickness > 1 else z1 / SliceThickness)

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(1, 2, 1, projection='3d')
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.voxels(x, y, z, filled, facecolors=facecolors, shade=False)
    ax.view_init(st_angle, angle)
    ax = fig.add_subplot(1, 2, 2, projection='3d')
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.voxels(x1, y1, z1, filled1, facecolors=facecolors1, shade=False)
    ax.view_init(st_angle, angle)

    if cmap == cm.afmhot:
        norm = matplotlib.colors.Normalize(vmin=160, vmax=1300)
        ticks_colors = [160, 300, 500, 800, 900, 1000, 1100, 1200, 1250, 1300]
        ticks_label = 'HU'
    else:
        norm = matplotlib.colors.Normalize(vmin=1.7, vmax=2.5)
        ticks_colors = [1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5]
        ticks_label = "гр/см3"

    p = ax.voxels(x1, y1, z1, filled1, facecolors=facecolors1, shade=False)
    m = cm.ScalarMappable(cmap=cmap, norm=norm)
    # m.set_array(p.astype(float))
    plt.colorbar(m, ax=ax, fraction=0.045, pad=0.1, ticks=ticks_colors, label=ticks_label)
    return fig


def stone_3proj_view(ds_array, frame_size_of_stone, realLength_stone, realHeight_stone, SliceThickness=1,
                     x_thin=1, y_thin=1, st_angle=15, angle=75, cmap=cm.afmhot):
    stone_HU_min = 0
    stone_HU_max = 1300
    vmin = stone_HU_min  # right_kidney_array.min()
    vmax = stone_HU_max  # right_kidney_array.max()
    steps = int((vmax - vmin) / 10)
    ticks = [i for i in range(vmin, vmax + steps, steps)]
    str_ticks = [i for i in ticks]

    # form coronal slic of stone
    sum_ligth = 0
    coronal_slice = 0
    max_ligth = 0
    if ds_array.shape[1] >= 1:
        for y in range(ds_array.shape[1]):
            if sum_ligth > max_ligth:
                max_ligth = sum_ligth
                coronal_slice = y
            sum_ligth = 0
            for z in range(ds_array.shape[0]):
                for x in range(ds_array.shape[2]):
                    sum_ligth += ds_array[z, y, x]
    else:
        coronal_slice = ds_array.shape[1] - 1

    # form sagittal slic of stone
    sum_ligth = 0
    sagittal_slice = 0
    max_ligth = 0
    if ds_array.shape[2] >= 1:
        for x in range(ds_array.shape[2]):
            if sum_ligth > max_ligth:
                max_ligth = sum_ligth
                sagittal_slice = x
            sum_ligth = 0
            for y in range(ds_array.shape[1]):
                for z in range(ds_array.shape[0]):
                    sum_ligth += ds_array[z, y, x]
    else:
        sagittal_slice = ds_array.shape[2] - 1

    # form axial slic of stone
    sum_ligth = 0
    axial_slice = 0
    max_ligth = 0
    if ds_array.shape[0] >= 1:
        for z in range(ds_array.shape[0]):
            if sum_ligth > max_ligth:
                max_ligth = sum_ligth
                axial_slice = z
            sum_ligth = 0
            for y in range(ds_array.shape[1]):
                for x in range(ds_array.shape[2]):
                    sum_ligth += ds_array[z, y, x]
    else:
        axial_slice = ds_array.shape[0] - 1

    # forn 3D model of stone
    stone_coronal = ds_array[:, coronal_slice, :]
    stone_sagittal = ds_array[:, :, sagittal_slice]
    stone_axial = ds_array[axial_slice, :, :]

    stone_coronal = cv2.resize(stone_coronal, frame_size_of_stone, interpolation=cv2.INTER_CUBIC)
    stone_sagittal = cv2.resize(stone_sagittal, frame_size_of_stone, interpolation=cv2.INTER_CUBIC)
    stone_axial = cv2.resize(stone_axial, frame_size_of_stone, interpolation=cv2.INTER_CUBIC)

    cube = ds_array[::-1, :, ::-1].T
    # cube = np.rot90(ds_array[:, :, :])
    cube = normalize(cube)
    facecolors = cmap(cube)
    facecolors[:, :, :, -1] = cube
    facecolors = explode(facecolors)
    filled = facecolors[:, :, :, -1] != 0
    x, y, z = expand_coordinates(np.indices(np.array(filled.shape) + 1))

    x = x * x_thin if x_thin > 1 else x / x_thin
    y = y * y_thin if y_thin > 1 else y / y_thin
    z = z * SliceThickness if SliceThickness > 1 else z / SliceThickness

    # plot figure
    fig = plt.figure(figsize=(15, 15))
    ax = fig.add_subplot(221)
    plt.title("Корональная проекция камня")
    plt.xlabel('Width, mm', fontsize=10)
    plt.ylabel('Height, mm', fontsize=10)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))

    coronal_img = ax.imshow(stone_coronal, origin='upper', cmap=plt.cm.inferno,
                            extent=(0, realLength_stone, 0, realHeight_stone), vmin=vmin, vmax=vmax)
    # Create axis for colorbar
    cbar_ax = make_axes_locatable(ax).append_axes(position='right', size='10%', pad=0.05)
    # Create colorbar
    cbar = fig.colorbar(mappable=coronal_img, cax=cbar_ax)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(str_ticks)

    ax = fig.add_subplot(222)
    plt.title("Саггитальная проекция камня")
    plt.xlabel('Width, mm', fontsize=10)
    plt.ylabel('Height, mm', fontsize=10)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))

    sagittal_img = ax.imshow(stone_sagittal, origin='upper', cmap=plt.cm.inferno,
                             extent=(0, realLength_stone, 0, realHeight_stone), vmin=vmin, vmax=vmax)
    # Create axis for colorbar
    cbar_ax = make_axes_locatable(ax).append_axes(position='right', size='10%', pad=0.05)
    # Create colorbar
    cbar = fig.colorbar(mappable=sagittal_img, cax=cbar_ax)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(str_ticks)

    ax = fig.add_subplot(223)
    plt.title("Аксиальная проекция камня")
    plt.xlabel('Width, mm', fontsize=10)
    plt.ylabel('Height, mm', fontsize=10)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))

    axial_img = ax.imshow(stone_axial, origin='upper', cmap=plt.cm.inferno,
                          extent=(0, realLength_stone, 0, realHeight_stone), vmin=vmin, vmax=vmax)
    # Create axis for colorbar
    cbar_ax = make_axes_locatable(ax).append_axes(position='right', size='10%', pad=0.05)
    # Create colorbar
    cbar = fig.colorbar(mappable=axial_img, cax=cbar_ax)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(str_ticks)

    ax = fig.add_subplot(224, projection='3d')
    plt.title("3D визуализация камня")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.voxels(x, y, z, filled, facecolors=facecolors, shade=False)
    ax.view_init(st_angle, angle)
    norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
    p = ax.voxels(x, y, z, filled, facecolors=facecolors, shade=False)
    m = cm.ScalarMappable(cmap=cmap, norm=norm)
    # m.set_array(p)
    # plt.colorbar(m, ax=ax, fraction=0.046, pad=0.1, ticks=ticks)
    plt.colorbar(m, ax=ax, fraction=0.02, pad=0.1, ticks=ticks, label='HU')

    # plt.show()
    return fig

'''
def kidney_3D_visualisation(values, SliceThickness, PixelSpacingX, PixelSpacingY):
    X, Y, Z = np.mgrid[0:values.shape[0], 0:values.shape[1], 0:values.shape[2]]
    values[values <= 35] = 0
    values = values.flatten()
    """ colorsmaps
    ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
     'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
     'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
     'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
     'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
     'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
     'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
     'orrd', 'oryel', 'oxy', 'peach', 'phase', 'picnic', 'pinkyl',
     'piyg', 'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn',
     'puor', 'purd', 'purp', 'purples', 'purpor', 'rainbow', 'rdbu',
     'rdgy', 'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar',
     'spectral', 'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn',
     'tealrose', 'tempo', 'temps', 'thermal', 'tropic', 'turbid',
     'turbo', 'twilight', 'viridis', 'ylgn', 'ylgnbu', 'ylorbr',
     'ylorrd']
    """
    data = go.Isosurface(
        x=(X * PixelSpacingX if PixelSpacingX > 1 else X / PixelSpacingX).flatten(),
        y=(Y * PixelSpacingY if PixelSpacingY > 1 else Y / PixelSpacingY).flatten(),
        z=(Z * SliceThickness if SliceThickness > 1 else Z / SliceThickness).flatten(),
        value=values.flatten(),
        isomin=25,
        isomax=159,
        colorscale='plasma',
        surface_count=5,
        colorbar_nticks=5,
        opacity=0.9,
    )

    fig = go.Figure(data)
    return fig


def stone_3D_visualisation(values, SliceThickness, PixelSpacingX, PixelSpacingY):
    X, Y, Z = np.mgrid[0:values.shape[0], 0:values.shape[1], 0:values.shape[2]]
    data = go.Isosurface(
        x=(X * PixelSpacingX if PixelSpacingX > 1 else X / PixelSpacingX).flatten(),
        y=(Y * PixelSpacingY if PixelSpacingY > 1 else Y / PixelSpacingY).flatten(),
        z=(Z * SliceThickness if SliceThickness > 1 else Z / SliceThickness).flatten(),
        value=values.flatten(),
        isomin=160,
        isomax=1350,
        colorscale='hot',  # 'inferno',
        # surface=dict(show=True, count=1, fill=0.9),
        slices=go.isosurface.Slices(
            x=go.isosurface.slices.X(show=True, locations=[-0.5, 0.5]),
            y=go.isosurface.slices.Y(show=True, locations=[-0.5, 0.5]),
            z=go.isosurface.slices.Z(show=True, locations=[-0.5, 0.5])
        ),
        caps=go.isosurface.Caps(
            z=dict(show=False),
            x=dict(show=False),
            y=dict(show=False)
        ),
        # opacity=0.5, # needs to be small to see through all surfaces
        surface_count=8,
        colorbar_nticks=8,
        opacity=0.5,
        surface_fill=0.98
    )

    layout = go.Layout(
        margin=dict(t=0, l=0, b=0),
        scene=dict(
            camera=dict(
                eye=dict(
                    x=PixelSpacingX,
                    y=PixelSpacingY,
                    z=SliceThickness)
            )
        )
    )
    fig = go.Figure(data)
    return fig
'''
