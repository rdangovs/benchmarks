#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: serve-data.py

import argparse
import os
import multiprocessing as mp
import socket

from tensorpack.dataflow import (
    send_dataflow_zmq, MapData, TestDataSpeed, FakeData, dataset,
    AugmentImageComponent, BatchData, PrefetchDataZMQ)
from tensorpack.utils import logger
from imagenet_utils import (
    fbresnet_augmentor, small_augmentor)

from zmq_ops import dump_arrays


def get_data(batch, augmentors):
    ds = dataset.ILSVRC12(args.data, 'train', shuffle=True)
    ds = AugmentImageComponent(ds, augmentors, copy=False)
    ds = BatchData(ds, batch, remainder=False)
    ds = PrefetchDataZMQ(ds, min(50, mp.cpu_count()))
    return ds


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', help='ILSVRC dataset dir')
    parser.add_argument('--fake', action='store_true')
    parser.add_argument('--aug', choices=['fbresnet', 'small'], default='fbresnet')
    parser.add_argument('--batch', help='per-GPU batch size',
                        default=32, type=int)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()

    os.environ['CUDA_VISIBLE_DEVICES'] = ''

    if args.fake:
        ds = FakeData(
            [[args.batch, 224, 224, 3], [args.batch]],
            1000, random=False, dtype=['uint8', 'int32'])
    else:
        augs = fbresnet_augmentor(True) if args.aug == 'fbresnet' else small_augmentor()
        ds = get_data(args.batch, augs)

    logger.info("Running on {}".format(socket.gethostname()))

    if args.benchmark:
        ds = MapData(ds, dump_arrays)
        TestDataSpeed(ds, warmup=300).start()
    else:
        send_dataflow_zmq(
            ds, 'ipc://@imagenet-train-b{}'.format(args.batch),
            hwm=150, format='zmq_ops', bind=True)
