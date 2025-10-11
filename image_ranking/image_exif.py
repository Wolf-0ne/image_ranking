import exifread
import logging

def get_exif(path: str) -> dict:
    # get exif data
    with open(path, 'rb') as f:
        return exifread.process_file(f, debug=True, stop_tag="MakerNote NoteVersion", extract_thumbnail=False)

    #interesting exif tags:
    #BlurWarning - not sure what these values show
    #FocusWarning
    #ExposureWarning
    #FocusMode
    #AFPointSet - could use these to target blur detection?
    #FocusPixel

def exif_match(exif_a, exif_b) -> bool:
    def get_camera_lens_exif(exif) -> tuple:
        return (
            str(exif.get('Image Make', None)),
            str(exif.get('Image Model', None)),
            str(exif.get('EXIF LensMake', None)),
            str(exif.get('EXIF LensModel', None))
        )

    a = get_camera_lens_exif(exif_a)
    b = get_camera_lens_exif(exif_b)

    invalid = all(element == 'None' for element in a)
    invalid = invalid and all(element == 'None' for element in b)

    return (a == b) or invalid