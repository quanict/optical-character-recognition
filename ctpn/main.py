import glob
import os
import shutil
import sys
import cv2 as open_cv
import numpy as np
import tensorflow as tf
from tensorflow.python.platform import gfile

sys.path.append(os.getcwd())
from lib.fast_rcnn.config import cfg, cfg_from_file
from lib.fast_rcnn.test import _get_blobs
from lib.text_connector.detectors import TextDetector
from lib.text_connector.text_connect_cfg import Config as TextLineCfg
from lib.rpn_msr.proposal_layer_tf import proposal_layer


imgPrintWindow = 0
def resize_im(im, scale, max_scale=None):
    scale_float = float(scale) / min(im.shape[0], im.shape[1])

    if max_scale != None and scale_float * max(im.shape[0], im.shape[1]) > max_scale:
        scale_float = float(max_scale) / max(im.shape[0], im.shape[1])

    return open_cv.resize(im, None, None, fx=scale_float, fy=scale_float, interpolation=open_cv.INTER_LINEAR), scale_float

def draw_boxes(img, image_name, boxes, scale):
    base_name = image_name.split('/')[-1]

    with open('data/results/' + 'res_{}.txt'.format(base_name.split('.')[0]), 'w') as file_log:
        for box in boxes:
            if np.linalg.norm(box[0] - box[1]) < 5 or np.linalg.norm(box[3] - box[0]) < 5:
                continue
            color = (0, 0, 0)
            if box[8] >= 0.9:
                color = (0, 255, 0)
            elif box[8] >= 0.8:
                color = (255, 0, 0)
            open_cv.line(img, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
            open_cv.line(img, (int(box[0]), int(box[1])), (int(box[4]), int(box[5])), color, 2)
            open_cv.line(img, (int(box[6]), int(box[7])), (int(box[2]), int(box[3])), color, 2)
            open_cv.line(img, (int(box[4]), int(box[5])), (int(box[6]), int(box[7])), color, 2)

            min_x = min(int(box[0] / scale), int(box[2] / scale), int(box[4] / scale), int(box[6] / scale))
            min_y = min(int(box[1] / scale), int(box[3] / scale), int(box[5] / scale), int(box[7] / scale))
            max_x = max(int(box[0] / scale), int(box[2] / scale), int(box[4] / scale), int(box[6] / scale))
            max_y = max(int(box[1] / scale), int(box[3] / scale), int(box[5] / scale), int(box[7] / scale))

            line = ','.join([str(min_x), str(min_y), str(max_x), str(max_y)]) + '\r\n'
            file_log.write(line)

    img_out = open_cv.resize(img, None, None, fx=1.0 / scale, fy=1.0 / scale, interpolation=open_cv.INTER_LINEAR)

    open_cv.imshow('result-img-draw', img_out)
    open_cv.waitKey(0)

def img_read(im_name):
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(('Demo for {:s}'.format(im_name)))
    img = open_cv.imread(im_name)
    if img is None:
        print('Img not exist')
        return

    img, scale = resize_im(img, scale=TextLineCfg.SCALE, max_scale=TextLineCfg.MAX_SCALE)
    blobs, im_scales = _get_blobs(img, None)

    # print('image read', blobs)

    if cfg.TEST.HAS_RPN:
        im_blob = blobs['data']
        blobs['im_info'] = np.array([[im_blob.shape[1], im_blob.shape[2], im_scales[0]]], dtype=np.float32)

    cls_prob, box_pred = sess.run([output_cls_prob, output_box_pred], feed_dict={input_img: blobs['data']})
    rois, _ = proposal_layer(cls_prob, box_pred, blobs['im_info'], 'TEST', anchor_scales=cfg.ANCHOR_SCALES)
    # print('img_read', blobs)
    # print('rois', rois)
    # print('box_pred', box_pred)

    scores = rois[:, 0]
    boxes = rois[:, 1:5] / im_scales[0]
    text_detector = TextDetector()
    boxes = text_detector.detect(boxes, scores[:, np.newaxis], img.shape[:2])
    draw_boxes(img, im_name, boxes, scale)

if __name__ == '__main__':
    # init session
    config = tf.ConfigProto(allow_soft_placement=True)
    sess = tf.Session(config=config)
    with gfile.FastGFile('data/ctpn.pb', 'rb') as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
        sess.graph.as_default()
        tf.import_graph_def(graph_def, name='')

    sess.run(tf.global_variables_initializer())

    input_img = sess.graph.get_tensor_by_name('Placeholder:0')
    output_cls_prob = sess.graph.get_tensor_by_name('Reshape_2:0')
    output_box_pred = sess.graph.get_tensor_by_name('rpn_bbox_pred/Reshape_1:0')

    cfg_from_file('ctpn/text.yml')
    img_path = os.path.join(cfg.DATA_DIR, 'insurance', '2808ninkeikazoku.jpg')
    image = open_cv.imread(img_path)

    #--- dilation on the green channel ---
    dilated_img = open_cv.dilate(image[:, :, 1], np.ones((7, 7), np.uint8))
    bg_img = open_cv.medianBlur(dilated_img, 21)

    #--- finding absolute difference to preserve edges ---
    diff_img = 255 - open_cv.absdiff(image[:, :, 1], bg_img)

    #--- normalizing between 0 to 255 ---
    norm_img = open_cv.normalize(diff_img, None, alpha=0, beta=255, norm_type=open_cv.NORM_MINMAX, dtype=open_cv.CV_8UC1)

    # scale = 0.5
    # scale = 1
    #
    # open_cv.imshow('norm_img', open_cv.resize(norm_img, (0, 0), fx=scale, fy=scale))
    # open_cv.waitKey(0)
    #
    # # --- Otsu threshold ---
    # th = open_cv.threshold(norm_img, 0, 255, open_cv.THRESH_BINARY | open_cv.THRESH_OTSU)[1]
    # open_cv.imshow('th', open_cv.resize(th, (0, 0), fx=scale, fy=scale))
    # open_cv.waitKey(0)

    img_read(img_path)

    open_cv.destroyAllWindows()