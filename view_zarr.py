import napari
import zarr

viewer = napari.Viewer()
data = zarr.open('merged_images.zarr', mode='r')

# Set contrast limits explicitly (adjust min/max to your data range)
viewer.add_image(data['0'], channel_axis=0, contrast_limits=[0, 4095],
  colormap=["magenta", "red", "green", "blue", "gray"], 
  name=["actin","lyzome","granzyme","TCR","borders"] )

napari.run()