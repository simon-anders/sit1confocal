library( reticulate )
#use_virtualenv( "./.venv" )
use_python("/usr/bin/python")

skimage.draw <- import( "skimage.draw" )
czifile <- import( "czifile" )
gc <- import( "gc" )

library( tidyverse )

polygon2mask <- function( corners, size=c(1888,1888) ) {
  skimage.draw$polygon2mask( as.integer(size), np_array(corners) )
}

load_shapes <- function() {
  py_run_string('\\
import pickle
with open("shapes.pckl","rb") as f:
    shapes = pickle.load(f)
')
  shapes <- py_to_r( py$shapes )
  py_run_string( 'del shapes' )
  shapes
}

shapes <- load_shapes()

tibble( imgname = names(shapes) ) %>%
mutate( subject = ifelse( str_detect( imgname, "pt" ), "pt", "ctrl" ) ) %>%
mutate( stack_idx = as.integer( str_extract( imgname, "\\d+$" ) ) ) %>%
arrange( subject, stack_idx ) %>%
mutate( short_name = sprintf( "G-%s-%02d", toupper(str_sub(subject,1,1)), stack_idx) ) -> imgtbl

tibble( imgname = names(shapes) ) %>%
left_join( imgtbl ) %>%
pull( short_name ) -> names(shapes)

get_img_path <- function( long_img_name ) {
  #paste0( "Microscopy_FH/2nd try_patient_hd/GranB/", imgname, ".czi" )
  paste0( "images_orig/GranB/", long_img_name, ".czi" )
}

load_image <- function( shimgname ) {
  imgtbl %>% filter( short_name == shimgname ) %>% pull( imgname ) -> imgname
  stopifnot( length(imgname) == 1 )
  #print(imgname)
  img_filename <- get_img_path( imgname )
  drop( czifile$imread( img_filename ) )
}

run_napari <- function( shimgname ) {
  imgtbl %>% filter( short_name == shimgname ) %>% pull( imgname ) -> limgname
  system2( py_exe(), c( "run_napari.py", get_img_path( limgname ), limgname, shimgname ) )
}

display <- function( img, ... ) {
  image( seq(1,dim(img)[2]), seq(1,dim(img)[1]), 
      t(img)[,seq(dim(img)[1],1,-1)], 
      asp=1, useRaster=TRUE, ... )
}

### End Setup Code ###


# Shapes are loaded
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

# Load image
img <- load_image( imgname )

# Display Channel 1, z-Layer 1
display( img[1,1,,] )

# Make max projection
display( apply( img[1,,,], c(2,3), max ) )

# Make a max projection, faster
maxproj <- do.call( pmax, asplit(img[1,,,],1) )
display( maxproj )

# Load all images
imgs <- sapply( names(shapes), load_image, simplify=FALSE )

##
  
tibble( imgname = names(shapes) ) %>%
group_by( imgname ) %>%
reframe( tibble( cell = seq_along(shapes[[imgname]]) ) ) %>%
#slice_head(n=3) %>%
group_by( imgname, cell ) %>%
reframe( {
  cat( "working on ", imgname, "\n" )
  cell_mask <- polygon2mask( shapes[[imgname]][[cell]] )
  tibble( 
    mask_area = sum(cell_mask),
    value = sum( apply( imgs[[imgname]][3,,,], 1, function(x) sum(x * cell_mask) ) ) )
})  %>%
mutate( subject = ifelse( str_detect( imgname, "pt" ), "pt", "ctrl" ) ) -> tbl

tbl %>%
mutate( imgname_short = st)

tbl %>%
ggplot() +
ggbeeswarm::geom_beeswarm(aes(x=subject,y=value)) #+ scale_y_log10()

tbl %>%
mutate( subject = ifelse( str_detect( imgname, "pt" ), "pt", "ctrl" ) ) %>%
ggplot() +
  geom_point(aes(x=mask_area,y=value,col=subject))


sapply( )

sapply( seq_along(shapes[[imgname]])
sum( apply( img[3,,,], 1, function(x) sum(x * cell_mask) ) )
