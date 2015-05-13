   
def determine_primary_disk_size(cls, boot_method, flavor, volume_size=0):
    if flavor.extra_specs.get('class') == 'onmetal':
        return 28
    elif boot_method == 'volume':
        return volume_size
    else:
        return flavor.disk

def determine_image_id(cls, boot_method, image):
    if boot_method == 'volume':
        return None
    return image.id