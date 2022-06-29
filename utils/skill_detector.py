from itertools import product

import numpy as np
from PIL import Image
import pytesseract

# from constant_loaders import load_ultimates

# ultIds = [ult["abilityId"] for ult in load_ultimates()['ultimates']]
# ult_icons = np.stack(
#     [np.asarray(Image.open(f'resources/abilities/{ult}.png'))[:, :, :3] / 255. for ult in ultIds])


class ResolutionException(Exception):
    pass


def find_coeffs(pb, pa):
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])

    A = np.matrix(matrix, dtype=np.float)
    B = np.array(pb).reshape(8)

    res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
    return np.array(res).reshape(8)


resolutions = {
    '1920x1080': {
        'perspective': [[(669, 140), (683, 341), (1250, 140), (1236, 341)],
                        [(669, 140), (669, 341), (1250, 140), (1250, 341)]],
        'offset': 58,
        'rows': [164, 262],
        'cols': [687, 785, 883, 981, 1078, 1176]
    },
    '1440x1080': {
        'perspective': [[(430, 140), (443, 341), (1009, 140), (996, 341)],
                        [(430, 140), (430, 341), (1009, 140), (1009, 341)]],
        'offset': 58,
        'rows': [162, 261],
        'cols': [446, 544, 641, 738, 835, 933]
    },
    '1728x1080': {
        # TODO: UPDATE THESE VALUES, REMOVE UNDERSCORE
        'perspective': [[(430, 140), (443, 341), (1009, 140), (996, 341)],
                        [(430, 140), (430, 341), (1009, 140), (1009, 341)]],
        'offset': 58,
        'rows': [163, 261],
        'cols': [591, 689, 787, 883, 981, 1078]
    }
}


def change_perspective(image_path, new_image_path):
    new_image: Image.Image = Image.open(image_path)
    width, height = new_image.size
    new_image = new_image.resize((round(width * (1080 / height)), 1080))

    key = f'{width}x{height}'
    if key not in resolutions:
        raise ResolutionException

    persp = resolutions[key]['perspective']

    p_coeffs = find_coeffs(*persp)
    new_image.transform((width, height), Image.PERSPECTIVE, p_coeffs,
                        Image.BICUBIC).save(new_image_path)


def extract_skills(image_path):
    new_image = Image.open(image_path)
    width, height = new_image.size

    key = f'{width}x{height}'
    if key not in resolutions:
        raise ResolutionException

    persp = resolutions[key]['perspective']
    offset = resolutions[key]['offset']
    rows = resolutions[key]['rows']
    cols = resolutions[key]['cols']

    p_coeffs = find_coeffs(*persp)
    new_image: Image.Image = new_image.transform((width, height), Image.PERSPECTIVE, p_coeffs,
                                                 Image.BICUBIC)
    skill_images = []
    for i, (row, col) in enumerate(product(rows, cols)):
        skill_images.append(
            (np.asarray(new_image.crop(box=[col, row, col + offset, row + offset]).resize((64, 64))) / 255.)[:, :, :3])
    return skill_images


def detect_skills(img):
    images = extract_skills(img)
    ids = []
    for img in images:
        diff = np.abs(ult_icons - img)
        err = diff.sum(axis=(1, 2, 3))
        ids.append(ultIds[np.argmin(err)])
    return ids

def ocr(img):
    img = Image.open(img)
    text = pytesseract.image_to_string(img)
    pass


if __name__ == '__main__':
    images = ocr('resources/16x9.png')
    # ids = []
    # for img in images:
    #     diff = np.abs(ult_icons - img)
    #     err = diff.sum(axis=(1, 2, 3))
    #     ids.append(ultIds[np.argmin(err)])
    #     pass
    pass
