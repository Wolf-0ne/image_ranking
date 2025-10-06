import os
import logging

import xml.etree.ElementTree as ET


def darktable_set_rating(xmp_filepath: str, rating: int, silent: bool = False):
    """
    Sets the darktable star rating in an XMP file.
    Creates the file if it does not exist.

    Args:
        xmp_filepath (str): The path to the XMP file.
        rating (int): The desired star rating (0-5).
    """

    #define xml namespace
    ns = {
        'xmp': 'http://ns.adobe.com/xap/1.0/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    }
    ET.register_namespace('xmp', ns['xmp'])
    ET.register_namespace('rdf', ns['rdf'])

    #create if file does not exist
    if not os.path.exists(xmp_filepath):

        # Create a minimal XMP structure with the rating
        xmp_template = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmp:Rating="{rating}"/>
</rdf:RDF>
</x:xmpmeta>
'''
        
        #open file and write template
        with open(xmp_filepath, 'w', encoding='utf-8') as f:
            f.write(xmp_template)

        #log created
        if not silent:
            logging.debug(f"Created new XMP file at {xmp_filepath} with rating {rating} star(s).")

        return
    
    #edit existing file
    else:

        try:

            #parse xmp file
            tree = ET.parse(xmp_filepath)

            #get xml root
            root = tree.getroot()

            # Find the rdf:Description element
            description = root.find(".//rdf:Description", ns)

            # set rating attribute
            if description is not None:
                description.set('{http://ns.adobe.com/xap/1.0/}Rating', str(rating))
                tree.write(xmp_filepath, encoding='utf-8', xml_declaration=True)
                if not silent:
                    logging.debug(f"Rating for {xmp_filepath} set to {rating} star(s).")

            # Create rating element if not found
            else:
                logging.warning(f"xmp:Rating element not found in {xmp_filepath}.")

        #file removed between check and parse
        except FileNotFoundError:
            logging.error(f"Error: XMP file not found at {xmp_filepath}")


# Example usage:
# Assuming you have an XMP file named 'my_photo.nef.xmp'
# set_darktable_rating('path/to/my_photo.nef.xmp', 4)