import glob, pathlib, pickle
import czifile
import napari

all_shapes = dict()

for filename in glob.glob("./*czi"):

    basename = pathlib.Path(filename).stem
    print(basename)

    img = czifile.imread(filename).squeeze()
    viewer = napari.Viewer()
    viewer.add_image(img.max(1), channel_axis=0, colormap=['red', 'green', 'blue', 'cyan'], name=basename )
    shapes_layer = viewer.add_shapes()
    shapes_layer.mode = 'add_polygon'
    napari.run()

    print(shapes_layer.data)
    print()

    all_shapes[basename] = shapes_layer.data

with open( "shapes.pckl", "wb" ) as f:
    pickle.dump( all_shapes, f )

print( "Written shapes to 'shapes.pckl'." )