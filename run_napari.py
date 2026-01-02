import sys
import pickle
import czifile
import napari

img_path = sys.argv[1]
img_longname = sys.argv[2]
img_shortname = sys.argv[3]

with open("shapes.pckl","rb") as f:
    shapes = pickle.load(f)

img = czifile.imread( img_path ).squeeze()

v = napari.Viewer()

v.add_image( img, 
  channel_axis=0, 
  colormap=["magenta", "red", "green", "blue"], 
  name=["phaloidin","lyzome","granzyme","TCR"] )

shapes_layer = v.add_shapes( name=img_shortname )
shapes_layer.data = shapes[img_longname]

napari.run()

