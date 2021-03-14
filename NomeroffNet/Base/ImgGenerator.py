import os
import json
import cv2
import numpy as np
import random


class ImgGenerator:

    def __init__(self,
                 dirpath,
                 img_w=295, img_h=64,
                 batch_size=32,
                 labels_counts=[14, 4], with_aug=0):

        self.HEIGHT = img_h
        self.WEIGHT = img_w
        self.batch_size = batch_size

        self.labels_counts = labels_counts

        img_dirpath = os.path.join(dirpath, 'img')
        ann_dirpath = os.path.join(dirpath, 'ann')
        self.samples = []
        for filename in os.listdir(img_dirpath):
            name, ext = os.path.splitext(filename)
            if ext == '.png':
                img_filepath = os.path.join(img_dirpath, filename)
                json_filepath = os.path.join(ann_dirpath, name + '.json')
                if os.path.exists(json_filepath):
                    description = json.load(open(json_filepath, 'r'))
                    self.samples.append([img_filepath, [
                        int(description["region_id"]),
                        int(description["count_lines"])]])

        self.n = len(self.samples)
        self.indexes = list(range(self.n))
        self.batch_count = int(self.n/batch_size)
        self.with_aug = with_aug
        self.rezero()

    def rezero(self):
        self.cur_index = 0
        random.shuffle(self.indexes)

    def build_data(self):
        self.paths = []
        self.discs = []
        for i, (img_filepath, disc) in enumerate(self.samples):
            self.paths.append(img_filepath)
            self.discs.append(
                [
                    np.eye(self.labels_counts[0])[disc[0]],
                    np.eye(self.labels_counts[1])[disc[1]]
                ]
            )

    def normalize(self, img, with_aug=False):
        if with_aug:
            from .aug import aug
            imgs = aug([img])
            img = imgs[0]
        img = cv2.resize(img, (self.WEIGHT, self.HEIGHT))
        img = img.astype(np.float32)

        # advanced normalisation
        img_min = np.amin(img)
        img -= img_min
        img_max = np.amax(img)
        img /= (img_max or 1)
        img[img == 0] = .0001
        return img

    def next_sample(self):
        self.cur_index += 1
        if self.cur_index >= self.n:
            self.cur_index = 0
        return self.paths[self.indexes[self.cur_index]], self.discs[self.indexes[self.cur_index]]

    def generator(self, with_aug=0):
        for j in np.arange(self.batch_count):
            Ys = [[], []]
            Xs = []
            for i in np.arange(self.batch_size):
                x, y = self.next_sample()
                img = cv2.imread(x)
                x = self.normalize(img, with_aug=with_aug)
                Xs.append(x)
                Ys[0].append(y[0])
                Ys[1].append(y[1])
            Ys[0] = np.array(Ys[0]).astype(np.float32)
            Ys[1] = np.array(Ys[1]).astype(np.float32)
            yield np.moveaxis(np.array(Xs), 3, 1), Ys

    def pathGenerator(self):
        for j in np.arange(self.batch_count):
            Ys = [[], []]
            Xs = []
            Paths = []
            for i in np.arange(self.batch_size):
                x, y = self.next_sample()
                Paths.append(x)
                img = cv2.imread(x)
                x = self.normalize(img)
                Xs.append(x)
                Ys[0].append(y[0])
                Ys[1].append(y[1])
            Ys[0] = np.array(Ys[0]).astype(np.float32)
            Ys[1] = np.array(Ys[1]).astype(np.float32)
            yield Paths, np.moveaxis(np.array(Xs), 3, 1), Ys