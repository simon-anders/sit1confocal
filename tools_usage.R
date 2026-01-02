source( "tools.R" )

# Shapes have been loaded
str( shapes )

# Images table here
imgtbl

# Images can be viewed with Napari
imgname <- "G-P-04"
run_napari( imgname )

# images can be loaded
img <- load_image( imgname )
str(img)


# Make a cell mask
cell <- 1
cell_mask <- polygon2mask( shapes[[imgname]][[cell]] )
display( cell_mask )

# Display Channel 1, z-Layer 1
display( img[1,1,,] )

# Make max projection
display( apply( img[1,,,], c(2,3), max ) )

# Make a max projection, faster
maxproj <- do.call( pmax, asplit(img[1,,,],1) )
display( maxproj )

# Load all images
imgs <- sapply( names(shapes), load_image, simplify=FALSE )

