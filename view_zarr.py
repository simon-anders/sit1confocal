import sys
import napari
import zarr

viewer = napari.Viewer()
data = zarr.open(sys.argv[1], mode='r')

# Set contrast limits explicitly (adjust min/max to your data range)
viewer.add_image(data['0'], channel_axis=0, contrast_limits=[0, 4095],
  colormap=["magenta", "red", "green", "blue", "gray"], 
  name=["phalloidin","lyzome","granzyme","TCR","borders"],
  scale =[0.5, 0.03529, 0.03529]) 

napari.run()