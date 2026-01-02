import numpy as np
import zarr
from czifile import imread as czi_imread
from pathlib import Path
from typing import List
import numcodecs
import re
from glob import glob

# Put path to files here:
GLOB = "images_orig/GranB/*.czi"

# Sort numerically by extracting the number before "zstack"
def extract_zstack_number(filename):
    match = re.search(r'zstack(\d+)\.czi', filename)
    return int(match.group(1)) if match else 0

# Get all CZI files from the specified directory
all_czi_files = glob(GLOB)
all_czi_files = sorted(all_czi_files, key=extract_zstack_number)

# Separate into patient and control based on filename
patient_files = [f for f in all_czi_files if "pt" in f.lower()]
control_files = [f for f in all_czi_files if "pt" not in f.lower()]

# Validate we have exactly 10 of each
assert len(patient_files) == 10, f"Expected 10 patient files, found {len(patient_files)}"
assert len(control_files) == 10, f"Expected 10 control files, found {len(control_files)}"

print(f"Control files: {control_files}")
print(f"Patient files: {patient_files}")

# Configuration
N_CHANNELS = 5  # 4 original + 1 grid channel
N_Z_LAYERS = 15
IMAGE_SIZE = 1888
N_IMAGES_PER_GROUP = 10
GRID_MARGIN = 5

# Output dimensions
output_shape = (
    N_CHANNELS,
    N_Z_LAYERS,
    2 * IMAGE_SIZE,  # y: control (top) + patient (bottom)
    N_IMAGES_PER_GROUP * IMAGE_SIZE  # x: 10 images side by side
)

# Zarr configuration
chunk_shape = (1, 7, IMAGE_SIZE, IMAGE_SIZE)  # 1 channel, half z-stack, 1 image tile
output_zarr = "merged_images.zarr"

print(f"Creating zarr array with shape: {output_shape}")
print(f"Chunk shape: {chunk_shape}")

# Create zarr array with compression
store = zarr.DirectoryStore(output_zarr)
root = zarr.group(store=store, overwrite=True)

# Create main array (level 0 - full resolution)
z_array = root.create_dataset(
    '0',
    shape=output_shape,
    chunks=chunk_shape,
    dtype='uint16',
    compressor=numcodecs.Blosc(cname='zstd', clevel=3, shuffle=numcodecs.Blosc.SHUFFLE)
)

# Add metadata
z_array.attrs['axis_names'] = ['c', 'z', 'y', 'x']
z_array.attrs['channel_names'] = ['actin', 'lysosome', 'granzyme', 'TCR', 'grid']

def load_and_place_images(file_list: List[str], y_offset: int, array: zarr.Array):
    """Load CZI images and place them in the zarr array."""
    for img_idx, filepath in enumerate(file_list):
        print(f"Processing: {filepath}")
        
        # Load CZI file
        # Expected shape after squeeze: (C, Z, Y, X)
        img_data = czi_imread(filepath).squeeze()
        
        # Dimension order is (C, Z, Y, X) - swap to (Z, C, Y, X)
        img_data = np.transpose(img_data, (1, 0, 2, 3))
        
        if img_data.ndim == 4:
            n_z, n_c, height, width = img_data.shape
        else:
            raise ValueError(f"Unexpected image shape after transpose: {img_data.shape}")
        
        # Validate dimensions
        assert n_c == 4, f"Expected 4 channels, got {n_c}"
        assert height == IMAGE_SIZE and width == IMAGE_SIZE, \
            f"Expected {IMAGE_SIZE}x{IMAGE_SIZE}, got {height}x{width}"
        assert n_z <= N_Z_LAYERS, f"Image has {n_z} z-layers, max is {N_Z_LAYERS}"
        
        # Calculate x position for this image
        x_offset = img_idx * IMAGE_SIZE
        
        # Place image data (first 4 channels)
        # Z-padding: place at the beginning, pad at the end with zeros
        for c in range(4):
            for z in range(n_z):
                array[c, z, y_offset:y_offset + IMAGE_SIZE, x_offset:x_offset + IMAGE_SIZE] = \
                    img_data[z, c, :, :]
        
        print(f"  Placed at y={y_offset}, x={x_offset}, z_layers={n_z}/{N_Z_LAYERS}")

# Process control images (top row, y=0 to IMAGE_SIZE)
print("\n=== Processing Control Images ===")
load_and_place_images(control_files, y_offset=0, array=z_array)

# Process patient images (bottom row, y=IMAGE_SIZE to 2*IMAGE_SIZE)
print("\n=== Processing Patient Images ===")
load_and_place_images(patient_files, y_offset=IMAGE_SIZE, array=z_array)

# Create grid in 5th channel (index 4)
print("\n=== Creating Grid ===")
grid_channel = np.zeros((N_Z_LAYERS, 2 * IMAGE_SIZE, N_IMAGES_PER_GROUP * IMAGE_SIZE), dtype='uint16')

for img_idx in range(N_IMAGES_PER_GROUP):
    x_start = img_idx * IMAGE_SIZE
    x_end = (img_idx + 1) * IMAGE_SIZE
    
    # Vertical lines (left and right edges of each image)
    for offset in range(-GRID_MARGIN, GRID_MARGIN + 1):
        # Left edge
        if 0 <= x_start + offset < grid_channel.shape[2]:
            grid_channel[:, :, x_start + offset] = 1
        # Right edge
        if 0 <= x_end - 1 + offset < grid_channel.shape[2]:
            grid_channel[:, :, x_end - 1 + offset] = 1

# Horizontal lines (top and bottom of control/patient groups)
for offset in range(-GRID_MARGIN, GRID_MARGIN + 1):
    # Top edge of control group
    if 0 <= 0 + offset < grid_channel.shape[1]:
        grid_channel[:, 0 + offset, :] = 1
    # Bottom edge of control / top edge of patient
    if 0 <= IMAGE_SIZE + offset < grid_channel.shape[1]:
        grid_channel[:, IMAGE_SIZE + offset, :] = 1
    # Bottom edge of patient group
    if 0 <= 2 * IMAGE_SIZE - 1 + offset < grid_channel.shape[1]:
        grid_channel[:, 2 * IMAGE_SIZE - 1 + offset, :] = 1

# Write grid to zarr
z_array[4, :, :, :] = grid_channel
print("Grid created in channel 4")

# Create multiscale pyramid (3 levels)
print("\n=== Creating Multiscale Pyramid ===")
for level in range(1, 3):
    scale_factor = 2 ** level
    downsampled_shape = (
        N_CHANNELS,
        N_Z_LAYERS,
        output_shape[2] // scale_factor,
        output_shape[3] // scale_factor
    )
    
    print(f"Creating level {level} with shape: {downsampled_shape}")
    
    # Create downsampled array
    downsampled = root.create_dataset(
        str(level),
        shape=downsampled_shape,
        chunks=(1, 7, min(512, downsampled_shape[2]), min(512, downsampled_shape[3])),
        dtype='uint16',
        compressor=numcodecs.Blosc(cname='zstd', clevel=3, shuffle=numcodecs.Blosc.SHUFFLE)
    )
    
    # Downsample each channel and z-layer
    for c in range(N_CHANNELS):
        for z in range(N_Z_LAYERS):
            # Read full resolution data
            full_res = z_array[c, z, :, :]
            
            # Simple downsampling by taking every nth pixel
            downsampled[c, z, :, :] = full_res[::scale_factor, ::scale_factor]
    
    print(f"  Level {level} complete")

# Add multiscale metadata
root.attrs['multiscales'] = [{
    'version': '0.4',
    'name': 'merged_czi_images',
    'axes': [
        {'name': 'c', 'type': 'channel'},
        {'name': 'z', 'type': 'space', 'unit': 'micrometer'},
        {'name': 'y', 'type': 'space', 'unit': 'micrometer'},
        {'name': 'x', 'type': 'space', 'unit': 'micrometer'}
    ],
    'datasets': [
        {'path': '0', 'coordinateTransformations': [
            {'type': 'scale', 'scale': [1, z_spacing, y_spacing, x_spacing]}
        ]},
        {'path': '1', 'coordinateTransformations': [
            {'type': 'scale', 'scale': [1, z_spacing, 2*y_spacing, 2*x_spacing]}
        ]},
        {'path': '2', 'coordinateTransformations': [
            {'type': 'scale', 'scale': [1, z_spacing, 4*y_spacing, 4*x_spacing]}
        ]}

    ]
}]

print(f"\n=== Complete! ===")
print(f"Zarr array saved to: {output_zarr}")
print(f"\nTo view in napari:")
print(f"  import napari")
print(f"  import zarr")
print(f"  viewer = napari.Viewer()")
print(f"  data = zarr.open('{output_zarr}', mode='r')")
print(f"  viewer.add_image(data['0'], channel_axis=0)")
