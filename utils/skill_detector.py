from itertools import product

import numpy as np
from PIL import Image

from utils.constant_loaders import load_ultimates

ultIds = [ult["abilityId"] for ult in load_ultimates()['ultimates']]
ult_icons = np.stack(
    [np.asarray(Image.open(f'resources/abilities/{ult}.png'))[:,:,:3] / 255. for ult in ultIds])

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


def extract1080(image_path):
    res1080a = [[(669, 140), (683, 341), (1250, 140), (1236, 341)],
                [(669, 140), (669, 341), (1250, 140), (1250, 341)]]
    offset = 58
    rows = [164, 262]
    cols = [688, 786, 883, 981, 1079, 1176]

    img = Image.open(image_path)
    width, height = img.size
    if width != 1920 or height != 1080:
        raise ResolutionException

    coeffs = find_coeffs(*res1080a)
    img: Image.Image = img.transform((width, height), Image.PERSPECTIVE, coeffs,
                                     Image.BICUBIC)
    images = []
    for i, (row, col) in enumerate(product(rows, cols)):
        images.append(
            np.asarray(img.crop(box=[col, row, col + offset, row + offset]).resize((64, 64))) /255.)
    return images

def detect_skills(img):
    images = extract1080(img)
    ids = []
    for img in images:
        diff = np.abs(ult_icons - img)
        err = diff.sum(axis=(1, 2, 3))
        ids.append(ultIds[np.argmin(err)])
    return ids

if __name__ == '__main__':
    images = extract1080('utils/test.webp')
    ids =[]
    for img in images:
        diff = np.abs(ult_icons - img)
        err = diff.sum(axis=(1, 2, 3))
        ids.append(ultIds[np.argmin(err)])
        pass
    pass
