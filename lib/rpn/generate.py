# --------------------------------------------------------
# Faster R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

from fast_rcnn.config import cfg
from utils.blob import im_list_to_blob
from utils.timer import Timer
from fast_rcnn.config import cfg, cfg_from_file, cfg_from_list, get_output_dir
import os
import numpy as np
import cv2

def _vis_proposals(im, dets, thresh=0.5):
    """Draw detected bounding boxes."""
    inds = np.where(dets[:, -1] >= thresh)[0]
    if len(inds) == 0:
        return

    class_name = 'obj'
    im = im[:, :, (2, 1, 0)]
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(im, aspect='equal')
    for i in inds:
        bbox = dets[i,:4]
        # bbox = coordinates_transfer(dets[i, :5])
        score = dets[i, -1]

        ax.add_patch(
            plt.Rectangle((bbox[0], bbox[1]),
                          bbox[2] - bbox[0],
                          bbox[3] - bbox[1], fill=False,
                          edgecolor='red', linewidth=3.5)
            )
        ax.text(bbox[0], bbox[1] - 2,
                '{:s} {:.3f}'.format(class_name, score),
                bbox=dict(facecolor='blue', alpha=0.5),
                fontsize=14, color='white')

    ax.set_title(('{} detections with '
                  'p({} | box) >= {:.1f}').format(class_name, class_name,
                                                  thresh),
                  fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.draw()

def _get_image_blob(im):
    """Converts an image into a network input.

    Arguments:
        im (ndarray): a color image in BGR order

    Returns:
        blob (ndarray): a data blob holding an image pyramid
        im_scale_factors (list): list of image scales (relative to im) used
            in the image pyramid
    """
    im_orig = im.astype(np.float32, copy=True)
    im_orig -= cfg.PIXEL_MEANS

    im_shape = im_orig.shape
    im_size_min = np.min(im_shape[0:2])
    im_size_max = np.max(im_shape[0:2])

    processed_ims = []

    assert len(cfg.TEST.SCALES) == 1
    target_size = cfg.TEST.SCALES[0]

    im_scale = float(target_size) / float(im_size_min)
    # Prevent the biggest axis from being more than MAX_SIZE
    if np.round(im_scale * im_size_max) > cfg.TEST.MAX_SIZE:
        im_scale = float(cfg.TEST.MAX_SIZE) / float(im_size_max)
    frac=1.0
    if im_scale*im_size_max*im_scale*im_size_min>frac*cfg.TEST.MAX_SIZE*target_size:
        im_scale = float(frac*target_size) / float(im_size_min)
    im = cv2.resize(im_orig, None, None, fx=im_scale, fy=im_scale,
                    interpolation=cv2.INTER_LINEAR)
    im_info = np.hstack((im.shape[:2], im_scale))[np.newaxis, :]

    # print 'im_info when getting img blob:', im_info

    processed_ims.append(im)

    # Create a blob to hold the input images
    blob = im_list_to_blob(processed_ims)

    return blob, im_info

def im_proposals(net, im):
    """Generate RPN proposals on a single image."""
    blobs = {}
    blobs['data'], blobs['im_info'] = _get_image_blob(im)

    # print 'blobs.data.shape', blobs['data'].shape  #600*900

    net.blobs['data'].reshape(*(blobs['data'].shape))
    net.blobs['im_info'].reshape(*(blobs['im_info'].shape))

    # print 'blobs.data.reshape', blobs['data'].shape   #600*900

    blobs_out = net.forward(
            data=blobs['data'].astype(np.float32, copy=False),
            im_info=blobs['im_info'].astype(np.float32, copy=False))

    scale = blobs['im_info'][0, 2]
    boxes = blobs_out['rois'][:, 1:].copy()
    boxes = boxes / scale
    scores = blobs_out['scores'].copy()
    return boxes, scores

def imdb_proposals(net, imdb, outdir):
    """Generate RPN proposals on all images in an imdb."""

    _t = Timer()
    imdb_boxes = [[] for _ in xrange(imdb.num_images)]
    imdb_scores = [[] for _ in xrange(imdb.num_images)]
    for i in xrange(imdb.num_images):
        print 'reading img:', imdb.image_path_at(i)
        im = cv2.imread(imdb.image_path_at(i))

        _t.tic()
        imdb_boxes[i], imdb_scores[i] = im_proposals(net, im)
        _t.toc()

################################################################################

        # output_dir = get_output_dir(imdb, net=None)
        # img_idx = str(imdb.image_index[i])[3:-6]
        # det_file = os.path.join(output_dir, img_idx.split('/')[0])
        # if not os.path.exists(det_file):
        #     os.mkdir(det_file)
        # det_file_x = os.path.join(det_file, img_idx.split('/')[1] + '.txt')
        # print 'det_file_test:', det_file_x
        # np.savetxt(det_file_x, imdb_boxes[i], fmt = '%.6f')

################################################################################

################################################################################
        result = np.hstack((imdb_boxes[i], imdb_scores[i]))
        output_dir = outdir
        det_file = os.path.join(output_dir, imdb.image_index[i]+'.txt')
        print 'det_file:', det_file
        np.savetxt(det_file, result, fmt = '%.6f')

################################################################################

        print 'im_proposals: {:d}/{:d} {:.3f}s' \
              .format(i + 1, imdb.num_images, _t.average_time)
        if 0:
            dets = np.hstack((imdb_boxes[i], scores))
            # from IPython import embed; embed()
            _vis_proposals(im, dets[:3, :], thresh=0.9)
            plt.show()

    return imdb_boxes
