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
  x <- seq(1,dim(img)[2])
  y <- seq(1,dim(img)[1])
  image( x, y, t(img)[,seq(dim(img)[1],1,-1)], 
      asp=1, useRaster=TRUE, yaxt="n", ... )
  ticks <- c(0, 500, 1000, 1500 )
  axis( 2, dim(img)[1] - ticks, ticks)
}

get_masks <- function(imgname) {
  reduce( sapply( seq_along(shapes[[imgname]]), function(cell) cell * polygon2mask( shapes[[imgname]][[cell]] ), simplify=FALSE ), `+` )
}
